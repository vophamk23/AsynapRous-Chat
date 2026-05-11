// Khai thác và bóc tách cấu trúc tham số (URL Parameters) làm định danh đích đến
const urlParams = new URLSearchParams(window.location.search);
const peerName = urlParams.get("peer"); // Dùng cho chat 1-1
const peerIP = urlParams.get("ip"); // Dùng cho chat 1-1
const peerPort = urlParams.get("port"); // Dùng cho chat 1-1
const groupName = urlParams.get("group_name"); // Dùng cho chat Nhóm

const username = document.cookie.match(/username=([^;]+)/)[1];

// Thiết lập tiêu đề khung chat
const peerNameEl = document.getElementById("peerName");
if (peerNameEl) {
  peerNameEl.style.display = "flex";
  peerNameEl.style.alignItems = "center";
  peerNameEl.style.gap = "0.4rem";
}

if (groupName) {
  const avatarUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(groupName)}&background=4f46e5&color=fff&rounded=true&bold=true`;
  document.getElementById("peerName").innerHTML = `<img src="${avatarUrl}" style="width: 24px; height: 24px; border-radius: 50%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);" /> Group: <strong style="font-weight:800;">${groupName}</strong>`;
  document.getElementById("peerName").style.background = "rgba(79, 70, 229, 0.1)"; // Xanh nhạt
  document.getElementById("peerName").style.color = "var(--primary-color)"; 
  
  const btnMembers = document.getElementById("btn-view-members");
  if (btnMembers) {
     btnMembers.style.display = "block";
     btnMembers.onclick = async () => {
         let trackerIP = "127.0.0.1";
         let trackerPort = "9000";
         try {
           const trRes = await fetch("/get-tracker");
           const trData = await trRes.json();
           if (trData.trackerIP) trackerIP = trData.trackerIP;
           if (trData.trackerPort) trackerPort = trData.trackerPort;
         } catch (err) {}
         
         const btnOriginText = btnMembers.innerText;
         btnMembers.innerText = "⏳ Loading...";
         btnMembers.disabled = true;
         
         try {
           const trackerResp = await fetch(`http://${trackerIP}:${trackerPort}/get-group-members?group_name=${encodeURIComponent(groupName)}`);
           
           if (!trackerResp.ok) throw new Error("Failed");
           const trackerData = await trackerResp.json();
           
           let membersList = trackerData.members;
           localStorage.setItem(`group_members_${groupName}`, JSON.stringify(membersList));
           
           const listElem = document.getElementById("members-list");
           listElem.innerHTML = "";
           membersList.forEach(memberObj => {
               const memberName = memberObj.username || memberObj;
               const memAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(memberName)}&background=random&color=fff&rounded=true&bold=true`;
               const li = document.createElement("li");
               li.style.padding = "0.75rem 1rem";
               li.style.borderBottom = "1px solid var(--card-border)";
               li.style.color = "var(--text-main)";
               li.style.display = "flex";
               li.style.alignItems = "center";
               li.style.gap = "0.75rem";
               li.innerHTML = `<img src="${memAvatar}" style="width: 32px; height: 32px; border-radius: 50%;" /> <span><strong>${memberName}</strong> ${memberName === username ? '<span style="color:var(--text-muted);font-size:0.8rem;">(You)</span>' : ''}</span>`;
               listElem.appendChild(li);
           });
           document.getElementById("members-modal-title").innerText = `Group members of '${groupName}'`;
           document.getElementById("members-modal").style.display = "flex";
         } catch(e) {
            console.warn("Lỗi gọi Tracker xem mem, thử dùng cache...", e);
            const cachedStr = localStorage.getItem(`group_members_${groupName}`);
            if (cachedStr) {
               let membersList = JSON.parse(cachedStr);
               const listElem = document.getElementById("members-list");
               listElem.innerHTML = "";
               membersList.forEach(memberObj => {
                   const memberName = memberObj.username || memberObj;
                   const memAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(memberName)}&background=random&color=fff&rounded=true&bold=true`;
                   const li = document.createElement("li");
                   li.style.padding = "0.75rem 1rem";
                   li.style.borderBottom = "1px solid var(--card-border)";
                   li.style.color = "var(--text-main)";
                   li.style.display = "flex";
                   li.style.alignItems = "center";
                   li.style.gap = "0.75rem";
                   li.innerHTML = `<img src="${memAvatar}" style="width: 32px; height: 32px; border-radius: 50%;" /> <span><strong>${memberName}</strong> ${memberName === username ? '<span style="color:var(--text-muted);font-size:0.8rem;">(You)</span>' : ''}</span>`;
                   listElem.appendChild(li);
               });
               document.getElementById("members-modal-title").innerText = `Group members of '${groupName}' (Cached)`;
               document.getElementById("members-modal").style.display = "flex";
            } else {
               alert("Connection error: Could not reach Tracker and no cache available.");
            }
         } finally {
            btnMembers.innerText = btnOriginText;
            btnMembers.disabled = false;
         }
     };
  }
} else if (peerName) {
  const avatarUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(peerName)}&background=random&color=fff&rounded=true&bold=true`;
  document.getElementById("peerName").innerHTML = `<img src="${avatarUrl}" style="width: 24px; height: 24px; border-radius: 50%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);" /> User: <strong style="font-weight:800;">${peerName}</strong>`;
  document.getElementById("peerName").style.background = "var(--card-border)"; // Xám
  document.getElementById("peerName").style.color = "var(--text-main)";
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
  const rowDiv = document.createElement("div");
  rowDiv.style.display = "flex";
  rowDiv.style.gap = "0.5rem";
  rowDiv.style.alignItems = "flex-end";
  rowDiv.style.marginBottom = "0.5rem";
  rowDiv.style.width = "100%";

  const avatarUrl = sender === "System" ? `https://ui-avatars.com/api/?name=Sys&background=ef4444&color=fff&rounded=true&bold=true` 
                  : (sender === "Me" || sender === username ? `https://ui-avatars.com/api/?name=${encodeURIComponent(username)}&background=10b981&color=fff&rounded=true&bold=true`
                  : `https://ui-avatars.com/api/?name=${encodeURIComponent(sender)}&background=random&color=fff&rounded=true&bold=true`);

  const imgHtml = `<img src="${avatarUrl}" style="width: 32px; height: 32px; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.15); flex-shrink: 0;" />`;

  const msgDiv = document.createElement("div");
  msgDiv.classList.add("message");
  msgDiv.style.marginBottom = "0"; // Override styles
  
  if (sender === username || sender === "Me" || sender === "System") {
    rowDiv.style.justifyContent = "flex-end";
    msgDiv.classList.add("self");
    let displayName = sender === "Me" ? username : sender;
    msgDiv.innerHTML = `<div style="font-size: 0.75rem; font-weight: 600; opacity: 0.8; margin-bottom: 2px;">${displayName}</div>${text}`;
    rowDiv.innerHTML = msgDiv.outerHTML + imgHtml;
  } else {
    rowDiv.style.justifyContent = "flex-start";
    msgDiv.classList.add("other");
    msgDiv.innerHTML = `<div style="font-size: 0.75rem; font-weight: 600; opacity: 0.8; margin-bottom: 2px;">${sender}</div>${text}`;
    rowDiv.innerHTML = imgHtml + msgDiv.outerHTML;
  }
  
  chatWindow.appendChild(rowDiv);
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

    let membersList = [];
    try {
      // 1. Hỏi Tracker lấy danh sách thành viên hiện tại của nhóm
      const trackerResp = await fetch(
        `http://${trackerIP}:${trackerPort}/get-group-members?group_name=${encodeURIComponent(groupName)}`,
      );

      if (!trackerResp.ok) {
        throw new Error("Failed to retrieve group information.");
      }
      const trackerData = await trackerResp.json();
      membersList = trackerData.members;
      localStorage.setItem(`group_members_${groupName}`, JSON.stringify(membersList));
    } catch (err) {
      console.warn("Lỗi kết nối Tracker. Dùng cache...", err);
      const cachedStr = localStorage.getItem(`group_members_${groupName}`);
      if (cachedStr) {
        membersList = JSON.parse(cachedStr);
      } else {
        appendMessage(
          "System",
          "Failed to retrieve group information and no cache available."
        );
        return;
      }
    }

    try {
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

      const d = new Date(now);
      const timeStr = d.getHours().toString().padStart(2, '0') + ":" + d.getMinutes().toString().padStart(2, '0');
      appendMessage("Me", `${text} <div style="font-size: 0.65rem; opacity: 0.6; margin-top: 4px; text-align: right;">${timeStr}</div>`); // Hiển thị trên màn hình mình
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
      const d = new Date(now);
      const timeStr = d.getHours().toString().padStart(2, '0') + ":" + d.getMinutes().toString().padStart(2, '0');
      appendMessage("Me", `${text} <div style="font-size: 0.65rem; opacity: 0.6; margin-top: 4px; text-align: right;">${timeStr}</div>`);
    } catch (err) {
      appendMessage("System", "Failed to send message to local backend.");
    }
  } else {
    appendMessage("System", "Error: No destination found.");
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
        let timeStr = "";
        if (msg.time_stamp) {
           const d = new Date(msg.time_stamp);
           timeStr = d.getHours().toString().padStart(2, '0') + ":" + d.getMinutes().toString().padStart(2, '0');
        }
        appendMessage(
          msg.sender,
          `${msg.message} <div style="font-size: 0.65rem; opacity: 0.6; margin-top: 4px; text-align: right;">${timeStr}</div>`,
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

// --- LOGIC GIAO DIỆN MỚI: SIDEBAR LỊCH SỬ CHAT (Giống Messenger) ---
// Khởi tạo bộ nhớ tạm để lưu trạng thái "đã đọc"
if (!localStorage.getItem('readTimestamps')) {
  localStorage.setItem('readTimestamps', JSON.stringify({}));
}

async function fetchSidebarData() {
  // Lấy Connected Peers
  let peers = {};
  try {
    const res = await fetch("/get-connected-peer");
    const pData = await res.json();
    peers = pData.peer_list || {};
  } catch(e) {}
  
  // Lấy Groups từ Tracker
  let groups = [];
  try {
    let trackerIP = "127.0.0.1"; let trackerPort = "9000";
    try {
      const trRes = await fetch("/get-tracker");
      const trData = await trRes.json();
      if (trData.trackerIP) trackerIP = trData.trackerIP;
      if (trData.trackerPort) trackerPort = trData.trackerPort;
    } catch(e){}
    const res2 = await fetch(`http://${trackerIP}:${trackerPort}/my-groups?username=${encodeURIComponent(username)}`);
    if (!res2.ok) throw new Error("Tracker failed");
    const gData = await res2.json();
    if(gData.groups) {
       groups = gData.groups;
       localStorage.setItem(`my_groups_${username}`, JSON.stringify(groups));
    }
  } catch(e) {
      const cached = localStorage.getItem(`my_groups_${username}`);
      if (cached) groups = JSON.parse(cached);
  }

  let chatItems = []; 

  // Thu thập tin nhắn của Peer
  for (let p of Object.keys(peers)) {
     try {
       const res = await fetch(`/get-messages?peer=${encodeURIComponent(p)}`);
       const data = await res.json();
       let msgs = data.messages || [];
       let lastMsg = msgs.length > 0 ? msgs[msgs.length-1] : null;
       
       let senderName = lastMsg ? (lastMsg.sender === username || lastMsg.sender === "Me" ? "You" : lastMsg.sender) : "";
       
       chatItems.push({
         id: p, name: p, type: 'peer',
         ip: peers[p][0], port: peers[p][1],
         lastMsgText: lastMsg ? `${senderName}: ${lastMsg.message}` : "No messages yet",
         lastTime: lastMsg ? lastMsg.time_stamp : "",
         timestampForSort: lastMsg ? new Date(lastMsg.time_stamp).getTime() : 0,
         isMine: lastMsg ? (lastMsg.sender === username || lastMsg.sender === "Me") : true
       });
     } catch(e){}
  }

  // Thu thập tin nhắn của Group
  for (let g of groups) {
     try {
       const res = await fetch(`/get-messages?peer=${encodeURIComponent(g.group_name)}`);
       const data = await res.json();
       let msgs = data.messages || [];
       let lastMsg = msgs.length > 0 ? msgs[msgs.length-1] : null;
       
       let senderName = lastMsg ? (lastMsg.sender === username || lastMsg.sender === "Me" ? "You" : lastMsg.sender) : "";
       
       chatItems.push({
         id: g.group_name, name: g.group_name, type: 'group',
         lastMsgText: lastMsg ? `${senderName}: ${lastMsg.message}` : "No messages yet",
         lastTime: lastMsg ? lastMsg.time_stamp : "",
         timestampForSort: lastMsg ? new Date(lastMsg.time_stamp).getTime() : 0,
         isMine: lastMsg ? (lastMsg.sender === username || lastMsg.sender === "Me") : true
       });
     } catch(e){}
  }

  // Sắp xếp theo timestamp giảm dần (mới nhất lên đầu)
  chatItems.sort((a,b) => b.timestampForSort - a.timestampForSort);

  // Render Sidebar
  const sidebarList = document.getElementById("sidebar-list");
  if (!sidebarList) return;
  sidebarList.innerHTML = "";
  
  const currentTarget = groupName || peerName;
  let readTimestamps = JSON.parse(localStorage.getItem('readTimestamps'));

  chatItems.forEach(item => {
    const div = document.createElement("div");
    const isActive = (item.name === currentTarget);
    
    // Đánh dấu đã đọc nếu đang mở khung chat này
    if (isActive && item.timestampForSort > 0) {
       readTimestamps[item.name] = item.timestampForSort;
       localStorage.setItem('readTimestamps', JSON.stringify(readTimestamps));
    }
    
    let isUnread = false;
    if (!item.isMine && item.timestampForSort > 0) {
       let lastRead = readTimestamps[item.name] || 0;
       if (item.timestampForSort > lastRead) isUnread = true;
    }
    
    div.style.padding = "0.75rem";
    div.style.borderRadius = "8px";
    div.style.cursor = "pointer";
    div.style.background = isActive ? "rgba(79, 70, 229, 0.1)" : "transparent";
    div.style.borderLeft = isActive ? "4px solid var(--primary-color)" : "4px solid transparent";
    div.style.transition = "all 0.2s ease";
    
    div.onmouseover = () => { if(!isActive) div.style.background = "var(--card-border)"; }
    div.onmouseout = () => { if(!isActive) div.style.background = "transparent"; }
    
    div.onclick = () => {
       // Lưu trạng thái đã đọc trước khi chuyển trang
       if (item.timestampForSort > 0) {
           readTimestamps[item.name] = item.timestampForSort;
           localStorage.setItem('readTimestamps', JSON.stringify(readTimestamps));
       }
       if (item.type === 'peer') {
           window.location.href = `/chat?peer=${encodeURIComponent(item.name)}&ip=${item.ip}&port=${item.port}`;
       } else {
           window.location.href = `/chat?group_name=${encodeURIComponent(item.name)}`;
       }
    };
    
    const badge = item.type === 'group' ? `<span style="font-size:0.65rem; background:var(--primary-color); color:white; padding:2px 4px; border-radius:4px; margin-left:4px;">Group</span>` : '';
    
    let shortMsg = item.lastMsgText;
    if (shortMsg.length > 30) shortMsg = shortMsg.substring(0, 30) + "...";
    
    let timeStr = "";
    if (item.lastTime) {
      const d = new Date(item.lastTime);
      timeStr = d.getHours().toString().padStart(2, '0') + ":" + d.getMinutes().toString().padStart(2, '0');
    }
    
    // Formatting chưa đọc (Unread) vs Đã đọc (Read)
    let titleColor = isUnread ? "var(--text-main)" : "var(--text-main)";
    let titleWeight = isUnread ? "800" : (isActive ? "700" : "600");
    let msgColor = isUnread ? "var(--primary-color)" : "var(--text-muted)";
    let msgWeight = isUnread ? "700" : "400";
    
    const avatarUrl = item.type === 'group' 
        ? `https://ui-avatars.com/api/?name=${encodeURIComponent(item.name)}&background=4f46e5&color=fff&rounded=true&bold=true` 
        : `https://ui-avatars.com/api/?name=${encodeURIComponent(item.name)}&background=random&color=fff&rounded=true&bold=true`;
    
    div.innerHTML = `
      <div style="display:flex; align-items:center; gap: 0.75rem;">
         <img src="${avatarUrl}" style="width: 44px; height: 44px; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex-shrink: 0;" />
         <div style="flex-grow: 1; overflow: hidden;">
             <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <strong style="color:${titleColor}; font-size:0.95rem; font-weight:${titleWeight};">${item.name} ${badge}</strong>
                <span style="font-size:0.7rem; color:${isUnread ? 'var(--primary-color)' : 'var(--text-muted)'}; font-weight:${isUnread ? '700' : '400'};">${timeStr}</span>
             </div>
             <div style="font-size:0.85rem; color:${msgColor}; font-weight:${msgWeight}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ${shortMsg}
             </div>
         </div>
      </div>
    `;
    sidebarList.appendChild(div);
  });
}

// Gọi ngay lập tức và đồng bộ cập nhật Sidebar mỗi 2 giây
fetchSidebarData();
setInterval(fetchSidebarData, 2000);
