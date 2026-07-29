import { Canvas, useFrame } from "@react-three/fiber";
import { Line, OrbitControls, Stars, useTexture } from "@react-three/drei";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import { AnimatePresence, motion, useScroll, useSpring } from "framer-motion";
import { ArrowUpRight, Menu, Pause, Play, Volume2, VolumeX, X } from "lucide-react";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { nodes, stages } from "./data";

const textureUrl =
  "https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg";
const cityLightsUrl =
  "https://threejs.org/examples/textures/planets/earth_lights_2048.png";
const cloudUrl =
  "https://threejs.org/examples/textures/planets/earth_clouds_1024.png";

const clamp = (v: number) => Math.min(1, Math.max(0, v));
const earthVertexShader = `varying vec2 vUv; varying vec3 vWorldNormal; void main(){vUv=uv;vWorldNormal=normalize(mat3(modelMatrix)*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`;
const earthFragmentShader = `uniform sampler2D dayMap;uniform sampler2D nightMap;uniform vec3 sunDirection;varying vec2 vUv;varying vec3 vWorldNormal;void main(){float lightDot=dot(normalize(vWorldNormal),normalize(sunDirection));float sun=smoothstep(-.12,.36,lightDot);float night=1.0-smoothstep(-.20,.08,lightDot);vec3 rawDay=texture2D(dayMap,vUv).rgb;float dayLum=dot(rawDay,vec3(.299,.587,.114));vec3 day=vec3(dayLum*.11,dayLum*.13,dayLum*.15);float cityMask=dot(texture2D(nightMap,vUv).rgb,vec3(.299,.587,.114));vec3 cityGlow=vec3(0.92,0.72,0.35)*pow(cityMask,1.65)*night*1.3;float rim=pow(1.0-max(dot(normalize(vWorldNormal),vec3(0.,0.,1.)),0.0),4.0);vec3 colour=day*(.05+.95*sun)+cityGlow+vec3(.22,.16,.06)*rim*.12;gl_FragColor=vec4(colour,1.0);}`;

const latLonToPoint = (lat: number, lon: number, radius = 2.03) => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -(radius * Math.sin(phi) * Math.cos(theta)),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
};

function Earth({ progress }: { progress: number }) {
  const group = useRef<THREE.Group>(null);
  const clouds = useRef<THREE.Mesh>(null);
  const [map, cityLights, cloudMap] = useTexture([
    textureUrl,
    cityLightsUrl,
    cloudUrl,
  ]);
  const uniforms = useMemo(
    () => ({
      dayMap: { value: map },
      nightMap: { value: cityLights },
      sunDirection: { value: new THREE.Vector3(4, 2, 5).normalize() },
    }),
    [map, cityLights],
  );

  useEffect(() => {
    map.colorSpace = THREE.SRGBColorSpace;
    cityLights.colorSpace = THREE.SRGBColorSpace;
  }, [map, cityLights]);

  useFrame((_, delta) => {
    if (group.current)
      group.current.rotation.y += delta * (progress < 0.12 ? 0.035 : 0.006);
    if (clouds.current) clouds.current.rotation.y += delta * 0.004;
  });

  return (
    <group ref={group} rotation={[0.2, -0.75, 0]}>
      <mesh>
        <sphereGeometry args={[2, 128, 128]} />
        <shaderMaterial
          uniforms={uniforms}
          vertexShader={earthVertexShader}
          fragmentShader={earthFragmentShader}
        />
      </mesh>
      <mesh ref={clouds} scale={1.007}>
        <sphereGeometry args={[2, 128, 128]} />
        <meshPhongMaterial
          map={cloudMap}
          transparent
          opacity={0.16}
          color="#e7d7af"
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

function TrustNetwork({ progress, liveNodes }: { progress: number; liveNodes?: any[] }) {
  const points = useMemo(() => {
    if (liveNodes && liveNodes.length > 0) {
      return liveNodes.map((n) => latLonToPoint(n.lat, n.lon));
    }
    return nodes.map(([lat, lon]) => latLonToPoint(lat, lon));
  }, [liveNodes]);

  const visible =
    clamp((progress - 0.315) / 0.035) * clamp((0.52 - progress) / 0.045);

  return (
    <group>
      {points.map((point, i) => (
        <mesh
          key={i}
          position={point}
          scale={visible * (i % 5 === 0 ? 1.6 : 1)}
        >
          <sphereGeometry args={[0.025, 12, 12]} />
          <meshBasicMaterial
            color={i > 18 && progress > 0.4 ? "#d15938" : "#e7c474"}
            transparent
            opacity={visible}
          />
        </mesh>
      ))}
      {points.slice(0, 16).map((point, i) => {
        const end = points[(i * 7 + 5) % points.length];
        const mid = point.clone().add(end).normalize().multiplyScalar(2.75);
        return (
          <Line
            key={`arc-${i}`}
            points={[point, mid, end]}
            color={i < 3 && progress > 0.38 ? "#d15938" : "#d6af58"}
            transparent
            opacity={visible * 0.57}
            lineWidth={0.55}
          />
        );
      })}
    </group>
  );
}

function StageVisual({ stageIndex, snapshot }: { stageIndex: number; snapshot?: any }) {
  const signalProvider = snapshot?.latest_signal?.provider || "NASA EONET";
  const signalTime = snapshot?.latest_signal?.timestamp || `${new Date().toISOString().slice(11, 19)} UTC`;

  const sourcesList = snapshot?.stage2_sources || [
    { name: "NASA EONET", status: "ACTIVE" },
    { name: "Open-Meteo (ECMWF)", status: "ACTIVE" },
    { name: "Open-Meteo (GFS/NOAA)", status: "ACTIVE" },
    { name: "Copernicus CAMS", status: "ACTIVE" },
    { name: "NOAA Space Weather", status: "ACTIVE" }
  ];

  const edgeCount = snapshot?.edge_count ?? 12;
  const famCount = snapshot?.independent_families ?? 6;
  const colBefore = snapshot?.collapse?.before != null ? String(snapshot.collapse.before).padStart(2, '0') : "03";
  const colAfter = snapshot?.collapse?.after != null ? String(snapshot.collapse.after).padStart(2, '0') : "01";
  const driftName = snapshot?.drift?.name || "NOAA GOES-16 (degraded)";
  const rawLower = snapshot?.bounds?.raw_lower ?? 0.42;
  const rawUpper = snapshot?.bounds?.raw_upper ?? 0.78;
  const fusedLower = snapshot?.bounds?.fused_lower ?? 0.91;
  const fusedUpper = snapshot?.bounds?.fused_upper ?? 0.96;
  const fusedVal = snapshot?.fused_confidence ?? 94;

  const content = [
    <div className="signal-visual" key="signal">
      <span className="signal-dot" />
      <div className="signal-ring ring-one" />
      <div className="signal-ring ring-two" />
      <small>UNVERIFIED SIGNAL</small>
      <strong>{signalProvider} · {signalTime}</strong>
    </div>,
    <div className="validation-visual" key="validation">
      <span className="visual-kicker">INDEPENDENCE CHECK</span>
      {sourcesList.map((item: any) => (
        <div className="source-row" key={item.name}>
          <i className={item.status === "ACTIVE" ? "" : "warn"} />
          <span>{item.name}</span>
          <b>{item.status === "ACTIVE" ? "CONFIRMED" : item.status}</b>
        </div>
      ))}
    </div>,
    <div className="graph-visual" key="graph">
      <span className="visual-kicker">CORROBORATION GRAPH</span>
      <svg viewBox="0 0 330 190" aria-label="Trust graph">
        <path d="M44 50L143 93 221 44 286 101M44 50L84 149 143 93 201 154 286 101M84 149L201 154 221 44" />
        <circle cx="44" cy="50" r="7" />
        <circle cx="143" cy="93" r="9" className="active" />
        <circle cx="221" cy="44" r="7" />
        <circle cx="286" cy="101" r="7" />
        <circle cx="84" cy="149" r="7" />
        <circle cx="201" cy="154" r="7" />
      </svg>
      <div className="visual-foot">{edgeCount} LINKS · {famCount} INDEPENDENT FAMILIES</div>
    </div>,
    <div className="collapse-visual" key="collapse">
      <span className="visual-kicker">DEPENDENCY COLLAPSE</span>
      <div className="collapse-nodes">
        <i />
        <i />
        <i />
        <b />
      </div>
      <div className="collapse-rule" />
      <div className="collapse-count">
        <strong>{colBefore} → {colAfter}</strong>
        <span>INDEPENDENT WEIGHT</span>
      </div>
    </div>,
    <div className="drift-visual" key="drift">
      <span className="visual-kicker">SOURCE HEALTH · {driftName}</span>
      <svg viewBox="0 0 330 126" aria-label="Sensor drift trend">
        <path className="grid" d="M0 28H330M0 63H330M0 98H330" />
        <path
          className="trend"
          d="M0 83 C35 76 43 68 72 74 S110 60 137 66 S180 48 207 60 S245 42 264 63 S302 94 330 33"
        />
        <line x1="265" y1="10" x2="265" y2="116" />
        <circle cx="265" cy="63" r="5" />
      </svg>
      <div className="visual-foot risk">CUSUM THRESHOLD EXCEEDED</div>
    </div>,
    <div className="confidence-visual" key="confidence">
      <span className="visual-kicker">FUSION INTERVAL</span>
      <div className="confidence-row">
        <span>NEW</span>
        <i className="wide" />
        <b>{rawLower}—{rawUpper}</b>
      </div>
      <div className="confidence-row">
        <span>FUSED</span>
        <i className="tight" />
        <b>{fusedLower}—{fusedUpper}</b>
      </div>
      <div className="confidence-value">
        {fusedVal}<span>%</span>
      </div>
    </div>,
  ][stageIndex];

  return (
    <AnimatePresence mode="wait">
      <motion.aside
        className="stage-visual"
        key={stageIndex}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.32 }}
      >
        {content}
      </motion.aside>
    </AnimatePresence>
  );
}

function CameraDirector({ progress }: { progress: number }) {
  const target = useMemo(() => new THREE.Vector3(), []);
  useFrame(({ camera }) => {
    const a = progress * Math.PI * 1.2;
    const r = 9.1 - Math.sin(Math.PI * progress) * 0.75;
    camera.position.lerp(
      new THREE.Vector3(
        Math.sin(a) * r,
        0.55 + Math.sin(progress * 7) * 0.38,
        Math.cos(a) * r,
      ),
      0.035,
    );
    target.set(Math.sin(a + 0.45) * 0.26, 0.03, Math.cos(a + 0.45) * 0.26);
    camera.lookAt(target);
  });
  return null;
}

function Scene({ progress, explore, liveNodes }: { progress: number; explore: boolean; liveNodes?: any[] }) {
  return (
    <Canvas
      dpr={[1, 1.75]}
      camera={{ position: [0, 0.55, 9.1], fov: 31 }}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
    >
      <color attach="background" args={["#03070b"]} />
      <ambientLight intensity={0.42} />
      <directionalLight position={[4, 3, 5]} intensity={2.3} color="#fff0ce" />
      <Stars
        radius={100}
        depth={50}
        count={2400}
        factor={2.2}
        saturation={0}
        fade
        speed={0.35}
      />
      <Suspense fallback={null}>
        <Earth progress={progress} />
        <TrustNetwork progress={progress} liveNodes={liveNodes} />
      </Suspense>
      <CameraDirector progress={progress} />
      <EffectComposer multisampling={0}>
        <Bloom intensity={1.05} luminanceThreshold={0.5} mipmapBlur />
        <Vignette eskil={false} offset={0.2} darkness={0.9} />
      </EffectComposer>
      <OrbitControls
        enabled={explore}
        enablePan={false}
        minDistance={3.6}
        maxDistance={10}
      />
    </Canvas>
  );
}

export function App({ onEnter }: { onEnter?: () => void }) {
  const container = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: container,
    offset: ["start start", "end end"],
  });
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 80,
    damping: 24,
  });
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  const [explore, setExplore] = useState(false);
  const [menu, setMenu] = useState(false);
  const [soundOn, setSoundOn] = useState(false);
  const [apiStages, setApiStages] = useState<any[] | null>(null);
  const [sourceCount, setSourceCount] = useState(0);
  const [snapshotData, setSnapshotData] = useState<any | null>(null);

  const toggleSound = () => {
    const next = !soundOn;
    setSoundOn(next);
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(next ? 587.33 : 293.66, ctx.currentTime);
        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.35);
      }
    } catch {
      // Graceful fallback
    }
  };

  useEffect(() => smoothProgress.on("change", setProgress), [smoothProgress]);
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(
      () => window.scrollBy({ top: 5, behavior: "smooth" }),
      25,
    );
    return () => clearInterval(timer);
  }, [running]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "e") setExplore((value) => !value);
      if (event.key === "Escape") setExplore(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => {
    fetch("http://localhost:8000/public/story-snapshot")
      .then((r) => r.json())
      .then((data) => {
        setSnapshotData(data);
        setApiStages(
          data.stages.map((s: any, i: number) => ({
            ...s,
            id: String(i + 1).padStart(2, "0"),
          })),
        );
        setSourceCount(data.source_count);
      })
      .catch(() => {});
  }, []);
  const stageData = apiStages || stages;
  const storyProgress = clamp((progress - 0.13) / 0.87);
  const stageIndex = Math.min(
    stageData.length - 1,
    Math.floor(storyProgress * stageData.length),
  );
  const stage = stageData[stageIndex];
  const panelOpacity =
    progress < 0.13
      ? 0
      : clamp((storyProgress * stages.length - stageIndex) * 5) *
        clamp((stageIndex + 1 - storyProgress * stages.length) * 5);
  const heroOpacity = clamp(1 - progress / 0.09);
  return (
    <main ref={container}>
      <div className="scene">
        <Scene progress={storyProgress} explore={explore} liveNodes={snapshotData?.nodes} />
      </div>
      <nav className={progress > 0.03 ? "nav nav-clear" : "nav"}>
        <a className="brand" href="#top">
          <span>V</span> VERIDION
        </a>
        <div className="nav-links">
          <a href="#method">Method</a>
          <a href="#network">Network</a>
          <a href="#access">Access</a>
          <button className="primary" style={{ padding: "6px 14px", fontSize: "12px", borderRadius: "100px", display: "inline-flex", alignItems: "center", gap: "4px" }} onClick={onEnter}>
            Dashboard <ArrowUpRight size={14} />
          </button>
        </div>
        <button
          className="menu-button"
          onClick={() => setMenu(!menu)}
          aria-label="Open navigation"
        >
          {menu ? <X /> : <Menu />}
        </button>
      </nav>
      {menu && (
        <div className="mobile-menu">
          <a href="#method" onClick={() => setMenu(false)}>Method</a>
          <a href="#network" onClick={() => setMenu(false)}>Network</a>
          <a href="#access" onClick={() => setMenu(false)}>Access</a>
          <button className="primary" style={{ padding: "8px 16px", fontSize: "13px" }} onClick={() => { setMenu(false); onEnter?.(); }}>
            Launch Dashboard <ArrowUpRight size={14} />
          </button>
        </div>
      )}
      <motion.section
        id="top"
        className="hero"
        style={{ opacity: heroOpacity }}
      >
        <div className="eyebrow">
          <i /> INTELLIGENCE, CORROBORATED <i />
        </div>
        <h1>
          The world is noisy.
          <br />
          <em>We find what holds.</em>
        </h1>
        <p>
          Veridion turns uncertain signals into defensible intelligence —
          tracing every claim back through the evidence that earns it.
        </p>
        <div className="hero-actions">
          <button
            className="primary"
            onClick={() => {
              setRunning(!running);
              window.scrollTo({ top: window.innerHeight, behavior: "smooth" });
            }}
          >
            {running ? (
              <Pause size={15} />
            ) : (
              <Play size={15} fill="currentColor" />
            )}{" "}
            {running ? "Pause trace" : "Run the trace"}
          </button>
          <button className="primary" style={{ background: "rgba(224, 214, 184, 0.12)", border: "1px solid rgba(224, 214, 184, 0.25)", color: "#e0d6b8" }} onClick={onEnter}>
            Open Dashboard <ArrowUpRight size={15} />
          </button>
          <button className="text-button" onClick={() => setExplore(!explore)}>
            {explore ? "Exit exploration" : "Explore the network"}{" "}
            <ArrowUpRight size={16} />
          </button>
        </div>
        <div className="scroll-cue">
          <span>SCROLL TO TRACE</span>
          <b />
        </div>
      </motion.section>
      <div className="stages">
        {stageData.map((item, index) => (
          <section
            className="stage-space"
            id={index === 0 ? "method" : index === 2 ? "network" : undefined}
            key={item.id}
          />
        ))}
      </div>
      {panelOpacity > 0.02 && (
        <>
          <motion.aside
            className="story-card"
            style={{ opacity: panelOpacity }}
          >
            <div className="stage-number">
              {stage.id} <span> / 06</span>
            </div>
            <div className="card-rule" />
            <p className="eyebrow left">{stage.eyebrow}</p>
            <h2>{stage.title}</h2>
            <p className="card-copy">{stage.copy}</p>
            <div className="metric">
              <strong>{stage.metric}</strong>
              <span>{stage.label}</span>
            </div>
            <small>{stage.detail}</small>
          </motion.aside>
          <StageVisual stageIndex={stageIndex} snapshot={snapshotData} />
        </>
      )}
      {panelOpacity > 0.02 && (
        <aside className="telemetry">
          <span>LIVE UTC</span>
          <strong>{new Date().toISOString().slice(11, 19)}</strong>
          <i />
          <span>MONITORED</span>
          <strong>
            {sourceCount > 0 ? sourceCount.toLocaleString() : "\u2014"} SOURCES
          </strong>
        </aside>
      )}
      <button 
        className={`sound ${soundOn ? "active" : ""}`} 
        onClick={toggleSound} 
        aria-label="Toggle sound"
        style={{ cursor: "pointer" }}
      >
        {soundOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
      </button>
      {explore && (
        <div className="explore-label">
          FREE FLIGHT <span>WASD · MOUSE · ESC</span>
        </div>
      )}
      <section id="access" className="closing">
        <p className="eyebrow">THE VERDICT</p>
        <h2>
          Every decision deserves
          <br />
          <em>an evidence trail.</em>
        </h2>
        <button className="primary" onClick={onEnter}>
          Enter the intelligence room <ArrowUpRight size={16} />
        </button>
      </section>
    </main>
  );
}
