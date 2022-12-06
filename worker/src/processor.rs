// Copyright(C) Facebook, Inc. and its affiliates.
use crate::worker::SerializedBatchDigestMessage;
use crate::worker::WorkerMessage;
use config::WorkerId;
use crypto::Digest;
use ed25519_dalek::Digest as _;
use ed25519_dalek::Sha512;
use log::warn;
use primary::WorkerPrimaryMessage;
use rayon::prelude::IntoParallelIterator;
use rayon::prelude::IntoParallelRefIterator;
use rayon::prelude::ParallelIterator;
use std::convert::TryInto;
use store::Store;
use tokio::sync::mpsc::{Receiver, Sender};
use ed25519_dalek::{
    Keypair as EdKeyPair, Signer as EdSigner,
};
use rand::rngs::OsRng;

#[cfg(test)]
#[path = "tests/processor_tests.rs"]
pub mod processor_tests;

/// Indicates a serialized `WorkerMessage::Batch` message.
pub type SerializedBatchMessage = Vec<u8>;

/// Hashes and stores batches, it then outputs the batch's digest.
pub struct Processor;

impl Processor {
    pub fn spawn(
        // Our worker's id.
        id: WorkerId,
        // The persistent storage.
        mut store: Store,
        // Input channel to receive batches.
        mut rx_batch: Receiver<SerializedBatchMessage>,
        // Output channel to send out batches' digests.
        tx_digest: Sender<SerializedBatchDigestMessage>,
        // Whether we are processing our own batches or the batches of other nodes.
        own_digest: bool,
        // Whether to simulate signature verification or not
        enable_verification: bool,
    ) {
        let (messages, signatures, public_keys): (Vec<_>, Vec<_>, Vec<_>) = if enable_verification { 
            let messages = (0..100_000u64).map(|i| i.to_le_bytes()).collect::<Vec<_>>();

            let (signatures, public_keys) = messages.par_iter().map(|message| { 
                let keypair = EdKeyPair::generate(&mut OsRng);
                let signature = keypair.sign(message);
                (signature, keypair.public)
            }).unzip();

            (messages, signatures, public_keys)
        } else {
            (vec!(), vec!(), vec!())
        };

        tokio::spawn(async move {
            let message_refs = messages.iter().map(|m| m.as_slice()).collect::<Vec<_>>();

            while let Some(batch) = rx_batch.recv().await {
                // Hash the batch.
                let digest = Digest(Sha512::digest(&batch).as_slice()[..32].try_into().unwrap());

                if enable_verification {
                    let batch_deser = bincode::deserialize::<WorkerMessage>(&batch).unwrap();
                    if let WorkerMessage::Batch(batch_deser) = batch_deser {
                        let count = std::cmp::min(100_000, batch_deser.len());
                        if batch_deser.len() > 100_000 {
                            warn!("Batch size maximum for signature verification surpassed! {}", batch_deser.len());
                        }
                        
                        (0..64).into_par_iter().for_each(|core| {
                            let start = (count*core)/64;
                            let end = std::cmp::min(count, count*(core+1)/64);
                            ed25519_dalek::verify_batch(&message_refs[start..end], &signatures[start..end], &public_keys[start..end]).unwrap();
                        });
                    }
                }

                // Store the batch.
                store.write(digest.to_vec(), batch).await;

                // Deliver the batch's digest.
                let message = match own_digest {
                    true => WorkerPrimaryMessage::OurBatch(digest, id),
                    false => WorkerPrimaryMessage::OthersBatch(digest, id),
                };
                let message = bincode::serialize(&message)
                    .expect("Failed to serialize our own worker-primary message");
                tx_digest
                    .send(message)
                    .await
                    .expect("Failed to send digest");
            }
        });
    }
}
