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
// Logic tạo nhóm
async function handleCreateGroup() {
  const groupName = prompt("Nhập tên nhóm bạn muốn tạo:");
  if (!groupName) return;

  // Lấy username từ trình duyệt
  const currentUsername = getUsernameFromCookie();

  let trackerIP = "127.0.0.1";
  let trackerPort = "9000";
  try {
    const trRes = await fetch("/get-tracker");
    const trData = await trRes.json();
    if (trData.trackerIP) trackerIP = trData.trackerIP;
    if (trData.trackerPort) trackerPort = trData.trackerPort;
  } catch (err) { console.warn("Lỗi lấy tracker:", err); }

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
    console.error("Lỗi khi tạo nhóm:", err);
    alert("Lỗi khi kết nối đến Tracker.");
  }
}

// Logic Trưởng nhóm mời người khác vào nhóm
async function handleAddMember() {
  const groupName = prompt("Nhập tên nhóm bạn muốn thêm người:");
  if (!groupName) return;

  const targetUser = prompt("Nhập Username của người bạn muốn mời vào nhóm:");
  if (!targetUser) return;

  const currentUsername = getUsernameFromCookie();
  let trackerIP = "127.0.0.1";
  let trackerPort = "9000";
  try {
    const trRes = await fetch("/get-tracker");
    const trData = await trRes.json();
    if (trData.trackerIP) trackerIP = trData.trackerIP;
    if (trData.trackerPort) trackerPort = trData.trackerPort;
  } catch (err) { console.warn("Lỗi lấy tracker:", err); }

  try {
    const resp = await fetch(
      `http://${trackerIP}:${trackerPort}/add-to-group`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Truyền 3 món: Tên nhóm, Người bị add (target_user), Người đang ra lệnh add (username)
        body: JSON.stringify({
          group_name: groupName,
          target_user: targetUser,
          username: currentUsername,
        }),
      },
    );
    const data = await resp.json();

    if (resp.ok) {
      alert("Thành công: " + data.message);
    } else {
      alert("Lỗi: " + data.message); // Sẽ báo lỗi nếu người bấm nút không phải Trưởng nhóm
    }
  } catch (err) {
    console.error("Lỗi khi thêm thành viên:", err);
    alert("Lỗi khi kết nối đến Tracker.");
  }
}

// Lắp đặt móc nối Event Listener bảo đảm cây DOM định hình hoàn chỉnh trước khi đổ dữ liệu Web
document.addEventListener("DOMContentLoaded", loadPeers);
