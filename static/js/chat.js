// Khai thác và bóc tách cấu trúc tham số (URL Parameters) làm định danh đích đến
const urlParams = new URLSearchParams(window.location.search);
const peerName = urlParams.get("peer"); // Dùng cho chat 1-1
const peerIP = urlParams.get("ip"); // Dùng cho chat 1-1
const peerPort = urlParams.get("port"); // Dùng cho chat 1-1
const groupName = urlParams.get("group_name"); // Dùng cho chat Nhóm

const username = document.cookie.match(/username=([^;]+)/)[1];

// Thiết lập tiêu đề khung chat
if (groupName) {
  document.getElementById("peerName").innerText = "Group: " + groupName;
} else if (peerName) {
  document.getElementById("peerName").innerText = peerName;
}

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
    let displayName = sender === "Me" ? username : sender;
    msgDiv.innerHTML = `<div style="font-size: 0.75rem; font-weight: 600; opacity: 0.8; margin-bottom: 2px;">${displayName}</div>${text}`;
  } else {
    msgDiv.classList.add("other");
    msgDiv.innerHTML = `<div style="font-size: 0.75rem; font-weight: 600; opacity: 0.8; margin-bottom: 2px;">${sender}</div>${text}`;
  }
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Xử lý gửi tin nhắn (Tự động phân luồng 1-1 hoặc Nhóm)
async function handleSendMessage(text) {
  const now = new Date().toISOString();

  if (groupName) {
    // [LUỒNG CHAT NHÓM]
    let trackerIP = "127.0.0.1";
    let trackerPort = "9000";
    try {
      const trRes = await fetch("/get-tracker");
      const trData = await trRes.json();
      if (trData.trackerIP) trackerIP = trData.trackerIP;
      if (trData.trackerPort) trackerPort = trData.trackerPort;
    } catch (err) { console.warn("Lỗi lấy tracker:", err); }

    try {
      // 1. Hỏi Tracker lấy danh sách thành viên hiện tại của nhóm
      const trackerResp = await fetch(
        `http://${trackerIP}:${trackerPort}/get-group-members?group_name=${encodeURIComponent(groupName)}`,
      );
      const trackerData = await trackerResp.json();

      if (!trackerResp.ok) {
        appendMessage(
          "System",
          trackerData.message || "Không thể lấy thông tin nhóm.",
        );
        return;
      }

      const membersList = trackerData.members;

      // 2. Gửi lệnh yêu cầu Peer Server của mình phát sóng tin nhắn
      await fetch("/send-group-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          group_name: groupName,
          message: text,
          time_stamp: now,
          members: membersList,
        }),
      });

      appendMessage("Me", text); // Hiển thị trên màn hình mình
    } catch (err) {
      console.error(err);
      appendMessage("System", "Failed to send group message.");
    }
  } else if (peerName && peerIP && peerPort) {
    // [LUỒNG CHAT 1-1] (Giữ nguyên logic cũ)
    try {
      await fetch(`/send-message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          receiver: peerName,
          ip: peerIP,
          port: peerPort,
          message: text,
          time_stamp: now,
        }),
      });
      appendMessage("Me", text);
    } catch (err) {
      appendMessage("System", "Failed to send message to local backend.");
    }
  } else {
    appendMessage("System", "Lỗi: Không tìm thấy đích đến.");
  }
}

sendBtn.onclick = () => {
  const text = messageInput.value.trim();
  if (!text) return;

  handleSendMessage(text);

  messageInput.value = "";
};

// Triển khai cơ chế Polling vòng lặp truy vấn lịch sử trò chuyện cục bộ để đồng bộ hóa giao diện
async function fetchMessages() {
  // Sử dụng groupName nếu đang ở chế độ nhóm, ngược lại dùng peerName
  const targetId = groupName || peerName;

  if (!targetId) return;
  try {
    const resp = await fetch(
      `/get-messages?peer=${encodeURIComponent(targetId)}`,
    );
    const data = await resp.json();
    chatWindow.innerHTML = ""; // Clear old messages

    if (data.messages && data.messages.length > 0) {
      data.messages.forEach((msg) => {
        appendMessage(
          msg.sender,
          `${msg.message} <small>${msg.time_stamp}</small>`,
        );
      });
    }
  } catch (err) {
    console.error(err);
  }
}

// Theo dõi biến thiên bàn phím
messageInput.addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendBtn.click();
  }
});

// Kích hoạt đồng hồ đếm nhịp (Polling Loop)
setInterval(fetchMessages, 1000);
