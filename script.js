// ================= IMAGE SLIDER =================
let images1 = [
    "images/img1.jpg",
    "images/img3.jpg",
    "images/img5.jpg",
    "images/img7.jpg"
];

let images2 = [
    "images/img2.jpg",
    "images/img4.jpg",
    "images/img6.jpg",
    "images/img8.jpg"
];

let index = 0;

setInterval(() => {
    index = (index + 1) % images1.length;
    document.getElementById("slide1").src = images1[index];
    document.getElementById("slide2").src = images2[index];
}, 7000);


// ================= WELCOME MESSAGE =================
window.onload = function() {
    let messages = document.getElementById("messages");
    
    let welcomeDiv = document.createElement("div");
    welcomeDiv.classList.add("message", "bot");
    welcomeDiv.innerHTML = `
        <div class="bubble">
            Welcome to HICAS AI Assistant 👋 <br>
            How can I help you today?
        </div>
    `;
    messages.appendChild(welcomeDiv);
    
    messages.scrollTop = messages.scrollHeight;
    
    // slight delay to feel natural
    setTimeout(() => speak("Welcome to HICAS AI Assistant. How can I help you today?"), 300);
}


// ================= VOICE FUNCTION =================
function speak(text) {
    if ('speechSynthesis' in window) {
        let speech = new SpeechSynthesisUtterance();
        speech.text = text;
        speech.lang = "en-US";
        speechSynthesis.speak(speech);
    }
}


// ================= MIC SMART VOICE =================
function startVoice() {
    let recognition = new webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.start();

    recognition.onresult = function(event) {
        let voiceText = event.results[0][0].transcript;
        document.getElementById("userInput").value = voiceText;
        sendMessage();
    }
}


// ================= ENTER KEY =================
document.getElementById("userInput").addEventListener("keypress", function(e) {
    if (e.key === "Enter") sendMessage();
});


// ================= QUICK BUTTON =================
function quickMsg(text) {
    document.getElementById("userInput").value = text;
    sendMessage();
}


// ================= CHATBOT =================
function sendMessage() {
    let inputField = document.getElementById("userInput");
    let input = inputField.value.trim();
    let messages = document.getElementById("messages");

    if (input === "") return;

    // 1. Add USER MESSAGE (permanent DOM node)
    let userDiv = document.createElement("div");
    userDiv.className = "message user";
    let userBubble = document.createElement("div");
    userBubble.className = "bubble";
    userBubble.innerHTML = input;
    userDiv.appendChild(userBubble);
    messages.appendChild(userDiv);
    messages.scrollTop = messages.scrollHeight;

    // Clear input
    inputField.value = "";

    // 2. Add TYPING INDICATOR (temporary DOM node)
    let typingDiv = document.createElement("div");
    typingDiv.className = "message bot";
    typingDiv.id = "typing-indicator";  // unique ID for removal
    let typingBubble = document.createElement("div");
    typingBubble.className = "bubble";
    typingBubble.innerHTML = `
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    typingDiv.appendChild(typingBubble);
    messages.appendChild(typingDiv);
    messages.scrollTop = messages.scrollHeight;

    // 3. Fetch reply from backend
    fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input })
    })
    .then(res => res.json())
    .then(data => {
        // Remove typing indicator safely
        let typing = document.getElementById("typing-indicator");
        if (typing) typing.remove();

        // Add BOT MESSAGE (permanent DOM node)
        let botDiv = document.createElement("div");
        botDiv.className = "message bot";
        let botBubble = document.createElement("div");
        botBubble.className = "bubble";
        botBubble.innerHTML = data.reply;
        botDiv.appendChild(botBubble);
        messages.appendChild(botDiv);
        messages.scrollTop = messages.scrollHeight;

        // Speak after short delay
        setTimeout(() => speak(data.reply), 600);
    })
    .catch(() => {
        // Remove typing on error
        let typing = document.getElementById("typing-indicator");
        if (typing) typing.remove();

        let errorDiv = document.createElement("div");
        errorDiv.className = "message bot";
        let errorBubble = document.createElement("div");
        errorBubble.className = "bubble";
        errorBubble.innerHTML = "Server connection error da...";
        errorDiv.appendChild(errorBubble);
        messages.appendChild(errorDiv);
        messages.scrollTop = messages.scrollHeight;
    });
} 

// Make Send button work without double call
document.getElementById("sendButton").addEventListener("click", sendMessage);