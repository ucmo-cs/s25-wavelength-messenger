function uint8ArrayToBase64(uint8array) {
    return window.btoa(String.fromCharCode.apply(null,uint8array));
}

function base64ToUint8Array(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++){
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}

function generateSymmetricKey(room_code, currentUsername, recipientPublic64) {
    
    var privateKeyJSON = JSON.parse(localStorage.getItem("wavelength_"+ currentUsername + "PrivateKey"));
    var privateKeyArray = base64ToUint8Array(privateKeyJSON.privateKey);
    var recipientPublicKey = base64ToUint8Array(recipientPublic64)

    const symmetricKey = nacl.randomBytes(nacl.secretbox.keyLength); //Create a symmetric key out of 32 random bytes (256 bits)
    const nonce = nacl.randomBytes(nacl.box.nonceLength);
    
    const encryptedSymmetric = nacl.box(
        symmetricKey,
        nonce,
        recipientPublicKey,
        privateKeyArray
    );

    localStorage.setItem("wavelength_" + room_code + "SymmetricKey", uint8ArrayToBase64(symmetricKey));
    const encryptedKeyBase64 = uint8ArrayToBase64(encryptedSymmetric);
    const nonceBase64 = uint8ArrayToBase64(nonce);

    return [encryptedKeyBase64, nonceBase64];
}

// document.addEventListener('DOMContentLoaded', async function() {
//     let encryptedKeyBase64, nonceBase64 = generateSymmetricKey(convo_id, currentUser)
//
//     async function sendSymmetricKey(convo_id, recipient, payload) {
//         try {
//             const response = await fetch('/api/send_symmetric_key', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json'
//                 },
//                 body: JSON.stringify({
//                     convo_id: convo_id,
//                     recipient_id: recipient,
//                     payload: payload
//                 })
//             });
//
//             if (response.ok) {
//                 console.log('Symmetric key sent successfully!');
//             } else {
//                 console.error('Failed to send symmetric key.');
//             }
//         } catch (error) {
//             console.error('Error:', error);
//         }
//     }
//
//     const payload = {
//         convo_id: convo_id,
//         encryptedKey: encryptedKeyBase64,
//         nonce: nonceBase64
//     };
//
//     await sendSymmetricKey(convo_id, recipientId, payload);
//
//   });