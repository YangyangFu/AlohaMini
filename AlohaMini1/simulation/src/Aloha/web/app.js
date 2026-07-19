"use strict";

const query = new URLSearchParams(window.location.search);
const bridgePort = query.get("bridge_port") || "9090";
const host = window.location.hostname || "localhost";
const bridgeScheme = window.location.protocol === "https:" ? "wss" : "ws";
const bridgeUrl = `${bridgeScheme}://${host}:${bridgePort}`;

const topics = {
  cmdVel: ["/cmd_vel", "geometry_msgs/msg/TwistStamped"],
  leftArm: ["/ui/left_arm_target", "std_msgs/msg/Float64MultiArray"],
  rightArm: ["/ui/right_arm_target", "std_msgs/msg/Float64MultiArray"],
  lift: ["/ui/lift_target", "std_msgs/msg/Float64"],
  leftGripper: ["/ui/left_gripper_target", "std_msgs/msg/Float64"],
  rightGripper: ["/ui/right_gripper_target", "std_msgs/msg/Float64"],
};

let socket = null;
let reconnectTimer = null;
let driveTimer = null;
let activeDriveButton = null;
let latestJointPositions = {};

const jointTargetIds = {
  vertical_move: "target-lift",
  left_joint6: "target-left_gripper",
  right_joint6: "target-right_gripper",
};

function bridgeSend(message) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(message));
  return true;
}

function advertise([topic, type]) {
  bridgeSend({ op: "advertise", topic, type });
}

function publish([topic], msg) {
  return bridgeSend({ op: "publish", topic, msg });
}

function subscribe(topic, type, throttleRate = 100) {
  bridgeSend({
    op: "subscribe",
    topic,
    type,
    throttle_rate: throttleRate,
    queue_length: 1,
  });
}

function setConnectionState(state, label) {
  const container = document.querySelector(".connection");
  container.classList.remove("connected", "disconnected");
  if (state) container.classList.add(state);
  document.getElementById("connection-label").textContent = label;
  document.querySelectorAll(".send-button, .drive-button").forEach((button) => {
    button.disabled = state !== "connected";
  });
}

function connect() {
  clearTimeout(reconnectTimer);
  setConnectionState("", "Connecting to ROS…");
  socket = new WebSocket(bridgeUrl);

  socket.addEventListener("open", () => {
    setConnectionState("connected", "ROS connected");
    Object.values(topics).forEach(advertise);
    subscribe("/joint_states", "sensor_msgs/msg/JointState", 100);
    subscribe("/omni_base_controller/odom", "nav_msgs/msg/Odometry", 150);
    subscribe("/odom", "nav_msgs/msg/Odometry", 150);
    subscribe("/ui/status", "std_msgs/msg/String", 0);
    addStatus("Connected to rosbridge");
  });

  socket.addEventListener("message", (event) => {
    let packet;
    try {
      packet = JSON.parse(event.data);
    } catch (error) {
      console.warn("Ignored non-JSON rosbridge packet", error);
      return;
    }
    if (packet.op !== "publish" || !packet.msg) return;
    if (packet.topic === "/joint_states") updateJointState(packet.msg);
    if (packet.topic === "/omni_base_controller/odom" || packet.topic === "/odom") {
      updateOdometry(packet.msg);
    }
    if (packet.topic === "/ui/status") addStatus(packet.msg.data);
  });

  socket.addEventListener("close", () => {
    stopBase(false);
    setConnectionState("disconnected", "ROS disconnected — retrying");
    reconnectTimer = window.setTimeout(connect, 2000);
  });

  socket.addEventListener("error", () => socket.close());
}

function addStatus(text) {
  const log = document.getElementById("status-log");
  if (log.children.length === 1 && log.firstElementChild.textContent.startsWith("Waiting")) {
    log.replaceChildren();
  }
  const item = document.createElement("li");
  item.textContent = text;
  log.prepend(item);
  while (log.children.length > 6) log.lastElementChild.remove();
}

function updateJointState(message) {
  const names = message.name || [];
  const positions = message.position || [];
  names.forEach((name, index) => {
    const position = positions[index];
    if (!Number.isFinite(position)) return;
    latestJointPositions[name] = position;
    const input = document.getElementById(jointTargetIds[name] || `target-${name}`);
    if (input && input.dataset.touched !== "true") {
      input.value = String(position);
      updateSliderOutput(input);
    }
  });

  document.getElementById("joint-state").textContent = Object.entries(latestJointPositions)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, position]) => `${name.padEnd(20)} ${position.toFixed(3)}`)
    .join("\n");
}

function updateOdometry(message) {
  const pose = message.pose?.pose;
  if (!pose) return;
  const q = pose.orientation;
  const yaw = Math.atan2(
    2 * (q.w * q.z + q.x * q.y),
    1 - 2 * (q.y * q.y + q.z * q.z),
  );
  document.getElementById("odom-x").textContent = `${pose.position.x.toFixed(2)} m`;
  document.getElementById("odom-y").textContent = `${pose.position.y.toFixed(2)} m`;
  document.getElementById("odom-yaw").textContent = `${(yaw * 180 / Math.PI).toFixed(1)}°`;
}

function twistMessage(vx, vy, wz) {
  return {
    header: { stamp: { sec: 0, nanosec: 0 }, frame_id: "base_link" },
    twist: {
      linear: { x: vx, y: vy, z: 0 },
      angular: { x: 0, y: 0, z: wz },
    },
  };
}

function sendDrive(vx, vy, wz) {
  const scale = Number(document.getElementById("speed-scale").value);
  const command = [vx * scale, vy * scale, wz * scale];
  publish(topics.cmdVel, twistMessage(...command));
  document.getElementById("base-command").textContent =
    `vx ${command[0].toFixed(2)} · vy ${command[1].toFixed(2)} · ω ${command[2].toFixed(2)}`;
}

function startBase(button) {
  stopBase(true);
  activeDriveButton = button;
  activeDriveButton.classList.add("active");
  const values = ["vx", "vy", "wz"].map((axis) => Number(button.dataset[axis] || 0));
  sendDrive(...values);
  driveTimer = window.setInterval(() => sendDrive(...values), 100);
}

function stopBase(sendStop = true) {
  clearInterval(driveTimer);
  driveTimer = null;
  if (activeDriveButton) activeDriveButton.classList.remove("active");
  activeDriveButton = null;
  if (sendStop) sendDrive(0, 0, 0);
}

function updateSliderOutput(input) {
  const output = input.closest("label")?.querySelector("output");
  if (!output) return;
  const value = Number(input.value);
  if (input.id === "target-lift") output.textContent = `${value.toFixed(3)} m`;
  else if (input.id.includes("gripper")) output.textContent = `${value.toFixed(2)} rad`;
  else output.textContent = value.toFixed(2);
}

function sendArm(side) {
  const positions = [...document.querySelectorAll(`input[data-arm="${side}"]`)]
    .map((input) => Number(input.value));
  publish(topics[`${side}Arm`], { layout: { dim: [], data_offset: 0 }, data: positions });
  addStatus(`Requested ${side} arm target`);
}

function setupControls() {
  document.querySelectorAll(".drive-button").forEach((button) => {
    button.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      button.setPointerCapture(event.pointerId);
      startBase(button);
    });
    button.addEventListener("pointerup", () => stopBase(true));
    button.addEventListener("pointercancel", () => stopBase(true));
    button.addEventListener("lostpointercapture", () => stopBase(true));
  });
  document.getElementById("base-stop").addEventListener("click", () => stopBase(true));

  const speed = document.getElementById("speed-scale");
  speed.addEventListener("input", () => {
    document.getElementById("speed-scale-value").textContent = `${Math.round(Number(speed.value) * 100)}%`;
  });

  document.querySelectorAll('input[type="range"]').forEach((input) => {
    input.addEventListener("input", () => {
      input.dataset.touched = "true";
      updateSliderOutput(input);
    });
  });

  document.querySelectorAll("[data-send-arm]").forEach((button) => {
    button.addEventListener("click", () => sendArm(button.dataset.sendArm));
  });
  document.getElementById("send-lift").addEventListener("click", () => {
    publish(topics.lift, { data: Number(document.getElementById("target-lift").value) });
    addStatus("Requested lift height");
  });
  document.querySelectorAll("[data-send-gripper]").forEach((button) => {
    button.addEventListener("click", () => {
      const side = button.dataset.sendGripper;
      const value = Number(document.getElementById(`target-${side}_gripper`).value);
      publish(topics[`${side}Gripper`], { data: value });
      addStatus(`Requested ${side} gripper target`);
    });
  });

  window.addEventListener("blur", () => stopBase(true));
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stopBase(true);
  });
}

function setupCameras() {
  document.querySelectorAll("[data-camera-topic]").forEach((image) => {
    const topic = encodeURIComponent(image.dataset.cameraTopic);
    image.src = `/stream?topic=${topic}`;
  });
}

setConnectionState("", "Connecting to ROS…");
setupControls();
setupCameras();
connect();
