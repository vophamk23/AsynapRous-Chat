// Truy vấn danh bạ các Peer đang duy trì luồng kết nối P2P khả dụng từ máy chủ cục bộ
async function getConnectedPeers() {
  try {
    const res = await fetch("/get-connected-peer");
    // Chuyển đổi định dạng bản tin HTTP Response thành phân vùng dữ liệu Object cục bộ
    const data = await res.json();
    console.log(data.peer_list);
    return data.peer_list;
  } catch (err) {
    console.error("Error fetching peers:", err);
    return {};
  }
}

// Trình chiếu lưu lượng khởi tạo cầu nối P2P và đệ trình siêu dữ liệu lên Peer Server
async function connectToPeer(username, ip, port, btn) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("ip", ip);
  formData.append("port", port);

  try {
    const resp = await fetch("/add-list", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });

    const data = await resp.json();
    console.log("Add response:", data);

    if (data.status === "success" || resp.status === 200) {
      btn.disabled = true;
      btn.innerText = "Connected";
    } else {
      alert("Failed to connect: " + data.message);
    }
  } catch (err) {
    console.error("Error connecting:", err);
  }
}
// Biểu thức chính quy (Regex) trích xuất thẻ định danh Username tích hợp trong chuỗi Cookie
function getUsernameFromCookie() {
  const match = document.cookie.match(/username=([^;]+)/);
  return match ? match[1] : null;
}

// Quy trình phức hợp: Rà soát Tracker, thu thập danh bạ mạng lưới và kết xuất bảng DOM (Data Table)
async function loadPeers() {
  let trackerIP, trackerPort;

  try {
    const trackerResp = await fetch("/get-tracker");
    const trackerData = await trackerResp.json();
    trackerIP = trackerData.trackerIP;
    trackerPort = trackerData.trackerPort;
  } catch (err) {
    console.error("Failed to load tracker.json:", err);
    return;
  }

  const username = getUsernameFromCookie() || "";
  const connectedPeers = await getConnectedPeers();

  try {
    const resp = await fetch(`http://${trackerIP}:${trackerPort}/get-list`);
    const data = await resp.json();
    const peers = data.peers;

    const table = document.getElementById("peerTable");
    table.innerHTML = `<tr>
            <th>Name</th><th>IP</th><th>Port</th><th>Action</th>
        </tr>`;

    Object.entries(peers)
      .filter(([name]) => name.trim() !== username.trim())
      .forEach(([name, info]) => {
        const row = table.insertRow();
        row.insertCell().innerText = name;
        row.insertCell().innerText = info.ip;
        row.insertCell().innerText = info.port;

        const btn = document.createElement("button");

        if (connectedPeers[name]) {
          btn.innerText = "Connected";
          btn.disabled = true;
        } else {
          btn.innerText = "Connect";
          btn.onclick = () => {
            connectToPeer(name, info.ip, info.port, btn);
            // btn.innerText = "Connected";
            // btn.disabled = true;
            // console.log("Connected peers:", connectedPeers);
          };
        }
        row.insertCell().appendChild(btn);
      });
  } catch (err) {
    console.error(err);
    const table = document.getElementById("peerTable");
    table.innerHTML += "<tr><td colspan='4'>Failed to load peers</td></tr>";
  }
}

function showCustomModal(title, fields, submitBtnText, callback) {
  const backdrop = document.createElement('div');
  backdrop.style.position = 'fixed'; backdrop.style.top = '0'; backdrop.style.left = '0';
  backdrop.style.width = '100vw'; backdrop.style.height = '100vh';
  backdrop.style.background = 'rgba(0,0,0,0.5)'; backdrop.style.backdropFilter = 'blur(4px)';
  backdrop.style.display = 'flex'; backdrop.style.alignItems = 'center'; backdrop.style.justifyContent = 'center';
  backdrop.style.zIndex = '9999';

  const modal = document.createElement('div');
  modal.style.background = 'var(--card-bg, white)';
  modal.style.padding = '2rem'; modal.style.borderRadius = '16px';
  modal.style.boxShadow = '0 10px 25px rgba(0,0,0,0.1)';
  modal.style.width = '100%'; modal.style.maxWidth = '400px';
  modal.style.border = '1px solid var(--card-border, #e5e7eb)';

  const h3 = document.createElement('h3');
  h3.textContent = title;
  h3.style.margin = '0 0 1.5rem 0';
  h3.style.color = 'var(--text-main, #111827)';

  modal.appendChild(h3);
  const inputs = {};

  fields.forEach((f, idx) => {
    const label = document.createElement('label');
    label.textContent = f.label;
    label.style.display = 'block';
    label.style.marginBottom = '0.5rem';
    label.style.fontSize = '0.875rem';
    label.style.fontWeight = '600';
    label.style.color = 'var(--text-main, #111827)';

    const input = document.createElement('input');
    input.type = 'text';
    input.style.width = '100%'; input.style.padding = '0.75rem';
    input.style.border = '1px solid var(--card-border, #d1d5db)';
    input.style.borderRadius = '8px'; input.style.marginBottom = '1.5rem';
    input.style.boxSizing = 'border-box'; input.style.fontFamily = 'inherit';
    input.style.background = 'var(--input-bg, white)';
    input.style.color = 'var(--text-main, #111827)';
    inputs[f.id] = input;

    modal.appendChild(label);
    modal.appendChild(input);
    if (idx === 0) setTimeout(() => input.focus(), 10);
  });

  const btnGroup = document.createElement('div');
  btnGroup.style.display = 'flex'; btnGroup.style.justifyContent = 'flex-end'; btnGroup.style.gap = '0.75rem';

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = 'Cancel';
  cancelBtn.style.padding = '0.5rem 1rem'; cancelBtn.style.border = '1px solid #d1d5db';
  cancelBtn.style.background = 'white'; cancelBtn.style.borderRadius = '8px';
  cancelBtn.style.cursor = 'pointer'; cancelBtn.style.fontWeight = '600';
  cancelBtn.style.color = '#4b5563';

  const submitBtn = document.createElement('button');
  submitBtn.textContent = submitBtnText;
  submitBtn.style.padding = '0.5rem 1rem'; submitBtn.style.border = 'none';
  submitBtn.style.background = 'var(--primary-color, #4f46e5)'; submitBtn.style.borderRadius = '8px';
  submitBtn.style.cursor = 'pointer'; submitBtn.style.fontWeight = '600';
  submitBtn.style.color = 'white';

  btnGroup.appendChild(cancelBtn); btnGroup.appendChild(submitBtn);
  modal.appendChild(btnGroup); backdrop.appendChild(modal);
  document.body.appendChild(backdrop);

  const cleanup = () => document.body.removeChild(backdrop);
  cancelBtn.onclick = () => { cleanup(); callback(null); };

  const handleSubmit = () => {
    cleanup();
    const res = {};
    Object.keys(inputs).forEach(k => res[k] = inputs[k].value.trim());
    callback(res);
  };
  submitBtn.onclick = handleSubmit;

  Object.values(inputs).forEach(input => {
    input.onkeydown = (e) => {
      if (e.key === 'Enter') handleSubmit();
      if (e.key === 'Escape') cancelBtn.click();
    };
  });
}

// Logic tạo nhóm
async function handleCreateGroup() {
  showCustomModal(
    "Create New Group", 
    [{id: 'groupName', label: 'Enter the name for your new group:'}], 
    "Create",
    async (res) => {
      if (!res || !res.groupName) return;
      const groupName = res.groupName;

      // Lấy username từ trình duyệt
      const currentUsername = getUsernameFromCookie();

      let trackerIP = "127.0.0.1";
      let trackerPort = "9000";
      try {
        const trRes = await fetch("/get-tracker");
        const trData = await trRes.json();
        if (trData.trackerIP) trackerIP = trData.trackerIP;
        if (trData.trackerPort) trackerPort = trData.trackerPort;
      } catch (err) { console.warn("Could not retrieve tracker info:", err); }

      try {
        const resp = await fetch(
          `http://${trackerIP}:${trackerPort}/create-group`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            // NHÉT THÊM USERNAME VÀO ĐÂY
            body: JSON.stringify({
              group_name: groupName,
              username: currentUsername,
            }),
          },
        );
        const data = await resp.json();
        alert(data.message);

        if (resp.ok) {
          window.location.href = "/view-my-channels";
        }
      } catch (err) {
        console.error("Error creating group:", err);
        alert("Connection error: Could not reach Tracker.");
      }
    }
  );
}

// Logic Trưởng nhóm mời người khác vào nhóm
async function handleAddMember() {
  showCustomModal(
    "Invite Member",
    [
      {id: 'groupName', label: 'Enter the group name:'},
      {id: 'targetUser', label: 'Enter the username to invite:'}
    ],
    "Invite",
    async (res) => {
      if (!res || !res.groupName || !res.targetUser) return;
      
      const currentUsername = getUsernameFromCookie();
      let trackerIP = "127.0.0.1";
      let trackerPort = "9000";
      try {
        const trRes = await fetch("/get-tracker");
        const trData = await trRes.json();
        if (trData.trackerIP) trackerIP = trData.trackerIP;
        if (trData.trackerPort) trackerPort = trData.trackerPort;
      } catch (err) { console.warn("Could not retrieve tracker info:", err); }

      try {
        const resp = await fetch(
          `http://${trackerIP}:${trackerPort}/add-to-group`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            // Truyền 3 món: Tên nhóm, Người bị add (target_user), Người đang ra lệnh add (username)
            body: JSON.stringify({
              group_name: res.groupName,
              target_user: res.targetUser,
              username: currentUsername,
            }),
          },
        );
        const data = await resp.json();

        if (resp.ok) {
          alert("Success: " + data.message);
        } else {
          alert("Error: " + data.message);
        }
      } catch (err) {
        console.error("Error adding member:", err);
        alert("Connection error: Could not reach Tracker.");
      }
    }
  );
}

// Lắp đặt móc nối Event Listener bảo đảm cây DOM định hình hoàn chỉnh trước khi đổ dữ liệu Web
document.addEventListener("DOMContentLoaded", loadPeers);
