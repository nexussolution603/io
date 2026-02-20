// Configuration – change this to your backend URL
const API_URL = 'http://127.0.0.1:5000/ask';  // for local development
// For production, use your actual backend URL, e.g.:
// const API_URL = 'https://your-domain.com/ask';

const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// Function to add a message to the chat
function addMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'nexus-message');
    messageDiv.textContent = text;
    chatBox.appendChild(messageDiv);
    // Scroll to bottom
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Function to send message to backend
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Display user message
    addMessage('user', message);
    userInput.value = '';

    // Show typing indicator (optional)
    const typingDiv = document.createElement('div');
    typingDiv.classList.add('message', 'nexus-message');
    typingDiv.textContent = 'NEXUS is thinking...';
    chatBox.appendChild(typingDiv);

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });

        // Remove typing indicator
        chatBox.removeChild(typingDiv);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        addMessage('nexus', data.response);
    } catch (error) {
        // Remove typing indicator
        if (chatBox.contains(typingDiv)) {
            chatBox.removeChild(typingDiv);
        }
        addMessage('nexus', 'Sorry, I encountered an error. Please try again later.');
        console.error('Error:', error);
    }
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Optional: Welcome message
window.addEventListener('load', () => {
    addMessage('nexus', 'Hello! I am NEXUS. How can I help you today?');
});