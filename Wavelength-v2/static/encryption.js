function base64ToUint8Array(base64) {
    return nacl.util.decodeBase64(base64);
}

function uint8ArrayToBase64(uint8array) {
    return nacl.util.encodeBase64(uint8array);
}

function encryptMessage(message){
    console.log("wavelength_" + room + "SymmetricKey");
    //Grab symmetric key from localstorage
    const symmetricKey = base64ToUint8Array(localStorage.getItem("wavelength_" + room + "SymmetricKey"));

    //Create nonce per message
    var nonce = nacl.randomBytes(24);
    console.log(message + " " + typeof(message));
    //Encrypt the message
    var base64Message = btoa(message);
    var messageArray = base64ToUint8Array(base64Message); //Turns message into Uint8Array

    var encryptedMessage = nacl.secretbox(
        messageArray,
        nonce,
        symmetricKey
    );

    encryptedMessage = uint8ArrayToBase64(encryptedMessage);
    nonce = uint8ArrayToBase64(nonce);
    return `${nonce}:${encryptedMessage}`;
}

function decryptMessage(encryptedMessage, nonce) {
    //Grab symmetric key from localstorage
    var symmetricKey = localStorage.getItem("wavelength_" + room + "SymmetricKey");
    console.log(symmetricKey);
    console.log("Key length:", symmetricKey.length);
    symmetricKey = base64ToUint8Array(symmetricKey);
    var msgArray = base64ToUint8Array(encryptedMessage);
    var nonceArray = base64ToUint8Array(nonce)
    var decrypted = nacl.secretbox.open(msgArray, nonceArray, symmetricKey);
    if (!decrypted) {
        throw new Error("Decryption failed");
    }
    decrypted = uint8ArrayToBase64(decrypted);
    var decryptedMessage = atob(decrypted);
    //console.log(decryptedMessage);
    return decryptedMessage;
}
