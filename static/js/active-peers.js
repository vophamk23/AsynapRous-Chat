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

    // Đảm bảo thao tác khởi tạo phím điều hướng quản trị luồng kênh được thiết lập độc lập
    // Add View Channels Button (if not exists)
    let viewBtn = document.getElementById("viewChannelsBtn");
    if (!viewBtn) {
      viewBtn = document.createElement("button");
      viewBtn.id = "viewChannelsBtn";
      viewBtn.style.marginTop = "10px";
      viewBtn.innerText = "View My Channels";
      viewBtn.onclick = () => {
        // Tái chuyển hướng (Redirect) không gian làm việc sang phân vùng hiển thị kênh tương tác
        // localStorage.setItem("connectedPeers", JSON.stringify(connectedPeers));
        window.location.href = "/view-my-channels";
      };
      document.body.appendChild(viewBtn);
    }
  } catch (err) {
    console.error(err);
    const table = document.getElementById("peerTable");
    table.innerHTML += "<tr><td colspan='4'>Failed to load peers</td></tr>";
  }
}

// Lắp đặt móc nối Event Listener bảo đảm cây DOM định hình hoàn chỉnh trước khi đổ dữ liệu Web
document.addEventListener("DOMContentLoaded", loadPeers);
