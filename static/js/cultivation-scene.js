import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js';

const canvas = document.getElementById('cultivation-bg');

if (canvas) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    preserveDrawingBuffer: true,
    powerPreference: 'low-power',
  });

  renderer.setClearColor(0xf8f5ed, 1);

  const root = new THREE.Group();
  const mountains = new THREE.Group();
  const mirror = new THREE.Group();
  scene.add(root);
  root.add(mountains, mirror);

  function ridgeShape(width, baseY, peaks) {
    const shape = new THREE.Shape();
    shape.moveTo(-width, -5);
    shape.lineTo(-width, baseY);
    peaks.forEach(([x, y]) => shape.lineTo(x, y));
    shape.lineTo(width, baseY - 0.25);
    shape.lineTo(width, -5);
    shape.lineTo(-width, -5);
    return shape;
  }

  function addRidge(peaks, baseY, color, opacity, z) {
    const geometry = new THREE.ShapeGeometry(ridgeShape(10, baseY, peaks));
    const material = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.z = z;
    mountains.add(mesh);
    return mesh;
  }

  const farRidge = addRidge(
    [[-8, -0.9], [-6.5, -0.25], [-5.1, -0.7], [-3.7, 0.1], [-2.1, -0.5], [-0.5, 0.25], [1.4, -0.35], [3.1, 0.18], [5.1, -0.55], [7, -0.1], [8.8, -0.65]],
    -1.25,
    0x8ea79a,
    0.34,
    -4.2,
  );
  const midRidge = addRidge(
    [[-8, -1.35], [-6.8, -0.55], [-5.6, -1.05], [-4.2, -0.15], [-2.8, -0.85], [-1.1, -0.05], [0.8, -0.9], [2.2, -0.25], [4.3, -1.0], [6.2, -0.45], [8.6, -1.1]],
    -1.85,
    0x536f67,
    0.28,
    -2.7,
  );
  const nearRidge = addRidge(
    [[-8, -2.2], [-6.7, -1.25], [-5.4, -1.75], [-4, -0.85], [-2.1, -1.55], [-0.4, -0.75], [1.2, -1.65], [3.2, -0.95], [4.9, -1.6], [6.6, -1.05], [8.7, -1.95]],
    -2.55,
    0x283a36,
    0.18,
    -1.4,
  );

  const gold = new THREE.MeshBasicMaterial({
    color: 0xb08a3c,
    transparent: true,
    opacity: 0.72,
    depthWrite: false,
  });
  const paleGold = new THREE.MeshBasicMaterial({
    color: 0xd9c589,
    transparent: true,
    opacity: 0.34,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  mirror.add(
    new THREE.Mesh(new THREE.TorusGeometry(0.84, 0.018, 16, 96), gold),
    new THREE.Mesh(new THREE.TorusGeometry(0.56, 0.01, 12, 96), gold),
    new THREE.Mesh(new THREE.CircleGeometry(0.5, 96), paleGold),
  );

  const spokeMaterial = new THREE.LineBasicMaterial({
    color: 0xb08a3c,
    transparent: true,
    opacity: 0.5,
  });
  for (let i = 0; i < 12; i += 1) {
    const a = (i / 12) * Math.PI * 2;
    const points = [
      new THREE.Vector3(Math.cos(a) * 0.61, Math.sin(a) * 0.61, 0.002),
      new THREE.Vector3(Math.cos(a) * 0.79, Math.sin(a) * 0.79, 0.002),
    ];
    mirror.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), spokeMaterial));
  }

  function addTrail(points, color, opacity) {
    const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(p[0], p[1], p[2])));
    const geometry = new THREE.TubeGeometry(curve, 80, 0.008, 8, false);
    const material = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(geometry, material);
    root.add(mesh);
    return mesh;
  }

  const trails = [
    addTrail([[-5.8, 1.25, -2.2], [-3.2, 1.65, -2.1], [-0.6, 1.05, -2.0], [1.8, 1.42, -2.1]], 0x9d7d3a, 0.28),
    addTrail([[-4.8, -0.3, -1.8], [-2.2, 0.25, -1.7], [0.4, -0.08, -1.7], [2.9, 0.55, -1.8]], 0x4f7f72, 0.2),
    addTrail([[1.4, 2.0, -2.4], [2.5, 1.45, -2.2], [3.3, 0.72, -2.0], [4.6, 0.5, -2.2]], 0xb08a3c, 0.24),
  ];

  const particleGeometry = new THREE.BufferGeometry();
  const particleCount = 150;
  const positions = new Float32Array(particleCount * 3);
  for (let i = 0; i < particleCount; i += 1) {
    positions[i * 3] = (Math.random() - 0.5) * 12;
    positions[i * 3 + 1] = Math.random() * 5.5 - 1.4;
    positions[i * 3 + 2] = Math.random() * -4 - 0.5;
  }
  particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const particles = new THREE.Points(
    particleGeometry,
    new THREE.PointsMaterial({
      color: 0x9a7b38,
      size: 0.028,
      transparent: true,
      opacity: 0.38,
      depthWrite: false,
    }),
  );
  root.add(particles);

  const clock = new THREE.Clock();
  let width = 0;
  let height = 0;

  function resize() {
    const nextWidth = window.innerWidth;
    const nextHeight = window.innerHeight;
    if (nextWidth === width && nextHeight === height) return;
    width = nextWidth;
    height = nextHeight;

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.7));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.position.set(0, 0.45, 8);
    camera.updateProjectionMatrix();

    const narrow = width < 720;
    mirror.position.set(narrow ? 2.1 : 3.35, narrow ? 1.45 : 0.95, -1.2);
    mirror.scale.setScalar(narrow ? 0.68 : 1);
    mountains.scale.set(narrow ? 0.92 : 1.1, narrow ? 0.92 : 1, 1);
  }

  function render() {
    resize();
    const t = clock.getElapsedTime();

    mirror.rotation.x = -0.18 + Math.sin(t * 0.32) * 0.035;
    mirror.rotation.y = 0.42 + Math.sin(t * 0.26) * 0.08;
    mirror.rotation.z = t * 0.09;

    particles.rotation.y = t * 0.008;
    farRidge.position.x = Math.sin(t * 0.08) * 0.05;
    midRidge.position.x = Math.sin(t * 0.07 + 1.8) * 0.07;
    nearRidge.position.x = Math.sin(t * 0.05 + 0.6) * 0.04;
    trails.forEach((trail, index) => {
      trail.position.y = Math.sin(t * 0.35 + index) * 0.035;
    });

    renderer.render(scene, camera);
  }

  function animate() {
    render();
    window.requestAnimationFrame(animate);
  }

  window.addEventListener('resize', resize);
  animate();
}
