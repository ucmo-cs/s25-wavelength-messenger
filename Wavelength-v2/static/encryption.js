function base64ToUint8Array(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++){
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}

function encryptMessage(message){

    //Grab symmetric key from localstorage
    const symmetricKey = base64ToUint8Array(localStorage.getItem("wavelength_" + convo_id + "SymmetricKey"));
    
    //Create nonce per message
    const nonce = nacl.randomBytes(nacl.secretBox.nonceLength);

    //Encrypt the message
    var messageArray = nacl.util.decodeUTF8(message); //Turns message into Uint8Array
    var encryptedMessage = nacl.secretBox(
        message,
        nonce,
        symmetricKey
    );

    return encryptedMessage, nonce;
}

function decryptMessage(encryptedMessage, nonce) {
    //Grab symmetric key from localstorage
    const symmetricKey = base64ToUint8Array(localStorage.getItem("wavelength_" + convo_id + "SymmetricKey"));

    var decrypted = nacl.secretbox.open(encrypted, nonce, key);
    if (!decrypted) {
        throw new Error("Decryption failed");
    }
    var decryptedMessage = nacl.util.encodeUTF8(decrypted);
    //console.log(decryptedMessage);
    return decryptedMessage;
}

document.getElementById("sendButton").addEventListener('submit', function(event) {
    event.preventDefault();

    try {
        var message = document.getElementById("messageBox").value;
        var encryptedMessage, nonce = encryptMessage(message);


        event.target.submit();
    } catch (err){
        console.log("Uh Oh. Error: ", err);
    }
})

