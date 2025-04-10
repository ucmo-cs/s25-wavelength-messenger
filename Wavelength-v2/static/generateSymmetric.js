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

function generateSymmetricKey(convo_id) {
    
    var privateKeyJSON = JSON.parse(localStorage.getItem("wavelength_"+ currentUsername + "PrivateKey"));
    var privateKeyArray = base64ToUint8Array(privateKeyJSON.privateKey);

    const symmetricKey = nacl.randomBytes(nacl.secretbox.keyLength); //Create a symmetric key out of 32 random bytes (256 bits)
    const nonce = nacl.randomBytes(nacl.box.nonceLength);
    
    const encryptedSymmetric = nacl.box(
        symmetricKey,
        nonce,
        recipientPublicKey,
        privateKeyArray
    );

    localStorage.setItem("wavelength_" + convo_id + "SymmetricKey", uint8ArrayToBase64(symmetricKey));
    const encryptedKeyBase64 = uint8ArrayToBase64(encryptedSymmetric);
    const nonceBase64 = uint8ArrayToBase64(nonce);

    return encryptedKeyBase64, nonceBase64;
}

document.addEventListener('DOMContentLoaded', function() {
    var encryptedKeyBase64, nonceBase64 = generateSymmetricKey()

    const payload = {
        encryptedKey: encryptedKeyBase64,
        nonce: nonceBase64
    };

    fetch('/save_encrypted_key', {
        method: 'POST',
        headers: {
            'Content-Type' : 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        console.log("Encrypted symmetric key saved: ", data);
    })
    .catch(error => console.error('Error saving key: ', error));

  });