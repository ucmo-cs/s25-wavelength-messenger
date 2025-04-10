// Utility function to convert ArrayBuffer to Base64 string
function arrayBufferToBase64(buffer) {
    const binary = String.fromCharCode.apply(null, new Uint8Array(buffer));
    return window.btoa(binary);
}

function generateAsyncKeys(event) {
    try {
        const keyPair = nacl.box.keyPair();

        const publicKeyBase64 = arrayBufferToBase64(keyPair.publicKey);
        const privateKeyBase64 = arrayBufferToBase64(keyPair.secretKey);

        //console.log(publicKeyBase64);
        //console.log(privateKeyBase64);

        try{
            const userData = {username: document.getElementById("username").value, privateKey: privateKeyBase64}
            localStorage.setItem("wavelength_"+ document.getElementById("username") + "PrivateKey", JSON.stringify(userData));
        } catch (err) {
            console.warn("LocalStorage is full or unavailable")
        }
        document.getElementById("publickey").value = publicKeyBase64;

        //Test that the privateKey made it to localstorage
    //            for (let i = 0; i < localStorage.length; i++) {
    //                let key = localStorage.key(i);
    //                let value = localStorage.getItem(key);
    //                console.log(`${key}: ${value}`);}
        event.target.submit();
    } catch (err){
        console.log("Uh Oh. Error: ", err);
    } 
}

