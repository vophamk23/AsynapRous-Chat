// Khai thác và bóc tách cấu trúc tham số (URL Parameters) làm định danh đích đến
const urlParams = new URLSearchParams(window.location.search);
const peerName = urlParams.get('peer');
const peerIP = urlParams.get('ip');
console.log(peerIP)
const peerPort = urlParams.get('port');
console.log(peerPort)
const username = document.cookie.match(/username=([^;]+)/)[1];
console.log(`http://${peerIP}:${peerPort}/receive-message`)

document.getElementById("peerName").innerText = peerName;

// Nhận diện và liên kết biến số định danh phiên người dùng hiển thị trực quan lên thành phần DOM
const ownerLabel = document.getElementById("currentOwnerName");
if (ownerLabel) ownerLabel.innerText = username;

const chatWindow = document.getElementById("messages");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");

// Kết xuất và lồng ghép cấu trúc khối tin nhắn (Message Node) lên giao diện Web UI
function appendMessage(sender, text) {
            if (!chatWindow) return;
            const msgDiv = document.createElement("div");
            msgDiv.classList.add("message");
            if (sender === username || sender === "Me" || sender === "System") {
                msgDiv.classList.add("self");
                let displayName = (sender === "Me") ? username : sender;
                msgDiv.innerHTML = `<div style="font-size: 0.75rem; font-weight: 600; opacity: 0.8; margin-bottom: 2px;">${displayName}</div>${text}`;
            } else {
                msgDiv.classList.add("other");
                msgDiv.innerHTML = `<div style="font-size: 0.75rem; font-weight: 600; opacity: 0.8; margin-bottom: 2px;">${sender}</div>${text}`;
            }
            chatWindow.appendChild(msgDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

// Điều phối mạch giao thức HTTP đẩy trực tiếp gói tin nhắn tới IP/Port của Peer (P2P Client-Side)
async function sendMessage(text) {
            if (!peerIP || !peerPort) {
                appendMessage("System", "Peer IP or port missing.");
                return;
            }
            const now = new Date().toISOString();
            try {
                await fetch(`http://${peerIP}:${peerPort}/receive-message`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"sender": username, "message": text, "time_stamp": now})
                });
                // appendMessage(username, text);
            } catch (err) {
                appendMessage("System", "Failed to send message to peer.");
            }
        }

// Triển khai cơ chế Polling vòng lặp truy vấn lịch sử trò chuyện cục bộ để đồng bộ hóa giao diện
async function fetchMessages() {
    if (!peerName) return;
    try {
        const resp = await fetch(`/get-messages?peer=${peerName}`);
        const data = await resp.json();
        chatWindow.innerHTML = ""; // Clear old messages
        data.messages.forEach(msg => {
            appendMessage(msg.sender, `${msg.message} <small>${msg.time_stamp}</small>`);
        });
    } catch (err) {
        console.error(err);
        appendMessage("System", "Failed to fetch messages");
    }
}

// Kích hoạt HTTP Request ghi nhận nhật ký phát tin từ bản thân vào cơ sở dữ liệu Peer Server
async function saveMessage(text) {
            if (!peerIP || !peerPort) {
                appendMessage("System", "Peer IP or port missing.");
                return;
            }
            const now = new Date().toISOString();
            try {
                await fetch(`/send-message`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"receiver": peerName, "message": text, "time_stamp": now})
                });
                // appendMessage(username, text);
            } catch (err) {
                appendMessage("System", "Failed to send message to peer.");
            }
        }

// Thiết lập bộ lắng nghe sự kiện Click (Pointer) điều hướng chu trình phát tin
sendBtn.onclick = () => {
    const text = messageInput.value.trim();
    if (!text) return;
    sendMessage(text);
    saveMessage(text);
    messageInput.value = "";
};

// Theo dõi biến thiên bàn phím (Keyboard Event), bổ trợ thao tác phím Enter đệ trình tin nhanh
messageInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendBtn.click();
    }
});

// Kích hoạt đồng hồ đếm nhịp (Polling Loop) tần số 1000ms kéo tin nhắn P2P theo thời gian thực
setInterval(fetchMessages, 1000);

