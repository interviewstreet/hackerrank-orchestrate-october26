import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber';
import { AdaptiveDpr, Billboard, Html, OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { CaseResult } from './types';
import { globeLayout, nodeColors } from './graphModel';
interface Props {
  result: CaseResult; selectedId: string | null; hoveredId: string | null; visible: Set<string>;
  path: { nodeIds: Set<string>; edgeIds: Set<string> }; animate: boolean; reduced: boolean;
  command: { action: string; sequence: number }; onSelect: (id: string) => void;
  onHover: (id: string | null) => void; onContextLost: () => void;
}
const home = new THREE.Vector3(0, 0, 7.2);
function Network(props: Props) {
  const { result, selectedId, hoveredId, visible, path, animate, reduced, command, onSelect, onHover } = props;
  const mesh = useRef<THREE.InstancedMesh>(null), assembly = useRef<THREE.Group>(null);
  const controls = useRef<OrbitControlsImpl>(null);
  const { camera, invalidate, gl, size, performance } = useThree();
  const fittedHome = useMemo(() => new THREE.Vector3(0, 0, 7.2 / Math.min(1, size.width / size.height)), [size.width, size.height]);
  const progress = useRef(reduced ? 1 : .8);
  const [moving, setMoving] = useState(false);
  const desired = useRef<{ position: THREE.Vector3; target: THREE.Vector3 } | null>(null);
  const positions = useMemo(() => globeLayout(result.graph_data.nodes), [result]);
  const curves = useMemo(() => result.graph_data.edges.flatMap(edge => {
    const a = positions.get(edge.source), b = positions.get(edge.target);
    if (!a || !b) return [];
    const start = new THREE.Vector3(...a), end = new THREE.Vector3(...b);
    return [{ edge, curve: new THREE.QuadraticBezierCurve3(start, start.clone().add(end).multiplyScalar(.56), end) }];
  }), [result, positions]);
  const edges = useMemo(() => {
    const verts: number[] = [], colors: number[] = [];
    curves.forEach(({ edge, curve }) => {
      const active = path.edgeIds.has(edge.id);
      const dim = (path.nodeIds.size > 0 && !active) || !visible.has(edge.source) || !visible.has(edge.target);
      const color = new THREE.Color(dim ? '#163d70' : active ? '#ffffff' : result.graph_data.nodes.some(n => n.id === edge.source && n.type === 'IDENTITY') ? '#ffc5f3' : '#65edff');
      if (!dim && !active) color.multiplyScalar(.65 + .35 * THREE.MathUtils.clamp((curve.getPoint(.5).z + 2.5) / 5, 0, 1));
      const points = curve.getPoints(15);
      for (let i = 0; i < points.length - 1; i++) { verts.push(...points[i].toArray(), ...points[i + 1].toArray()); colors.push(...color.toArray(), ...color.toArray()); }
    });
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3)); return geometry;
  }, [curves, path, visible]);
  useEffect(() => () => edges.dispose(), [edges]);
  const edgeGlow = useMemo(() => {
    const tubes = curves.filter(({ edge }) => visible.has(edge.source) && visible.has(edge.target) && (!path.edgeIds.size || path.edgeIds.has(edge.id)))
      .map(({ curve }) => new THREE.TubeGeometry(curve, 16, .014, 4, false));
    const merged = tubes.length ? mergeGeometries(tubes) : new THREE.BufferGeometry();
    tubes.forEach(t => t.dispose()); return merged;
  }, [curves, visible, path]);
  useEffect(() => () => edgeGlow.dispose(), [edgeGlow]);
  const activeFlowIds = useMemo(() => new Set(result.steps.filter(s => s.phase === 'FINDING' && s.operation === 'REPORT_ACTIVE_DATA_FLOW').map(s => s.resource_id)), [result]);
  const flowCurves = useMemo(() => curves.filter(({ edge }) => activeFlowIds.has(edge.source) || activeFlowIds.has(edge.target)), [curves, activeFlowIds]);
  useEffect(() => {
    if (!mesh.current) return;
    const transform = new THREE.Object3D();
    result.graph_data.nodes.forEach((node, index) => {
      transform.position.set(...positions.get(node.id)!);
      const dimmed = !visible.has(node.id) || (path.nodeIds.size > 0 && !path.nodeIds.has(node.id));
      const size = node.type === 'IDENTITY' ? .125 : ['SYSTEM', 'BACKUP'].includes(node.type) ? .075 : node.status === 'ISSUE' ? .085 : .055;
      transform.scale.setScalar(size * (node.id === hoveredId ? 1.5 : 1)); transform.updateMatrix();
      mesh.current!.setMatrixAt(index, transform.matrix);
      mesh.current!.setColorAt(index, new THREE.Color(dimmed ? '#28527c' : node.type === 'IDENTITY' ? '#fff2ff' : nodeColors[node.status]).lerp(new THREE.Color('#ffffff'), dimmed ? 0 : .62));
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    if (mesh.current.instanceColor) mesh.current.instanceColor.needsUpdate = true;
    invalidate();
  }, [result, positions, visible, path, hoveredId, invalidate]);
  useEffect(() => {
    if (selectedId && positions.has(selectedId)) {
      const target = new THREE.Vector3(...positions.get(selectedId)!);
      const direction = target.length() > .01 ? target.clone().normalize() : new THREE.Vector3(0, 0, 1);
      desired.current = { target: target.clone().multiplyScalar(.4), position: direction.multiplyScalar(7.8).add(new THREE.Vector3(0, .25, 0)) };
      setMoving(true); invalidate();
    }
  }, [selectedId, positions, invalidate]);
  useEffect(() => {
    if (!controls.current) return;
    const target = controls.current.target.clone(), offset = camera.position.clone().sub(target);
    if (command.action === 'reset') desired.current = { position: fittedHome.clone(), target: new THREE.Vector3() };
    else if (command.action === 'rotate') desired.current = { position: offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 6).add(target), target };
    else { offset.setLength(THREE.MathUtils.clamp(offset.length() * (command.action === 'in' ? .8 : 1.25), 4, 14)); desired.current = { position: target.clone().add(offset), target }; }
    setMoving(true); invalidate();
  }, [command, camera, invalidate, fittedHome]);
  useEffect(() => { gl.domElement.style.cursor = hoveredId ? 'pointer' : 'grab'; }, [hoveredId, gl]);
  useFrame((_, delta) => {
    if (assembly.current && progress.current < 1) { progress.current = reduced ? 1 : Math.min(1, progress.current + delta * .7); assembly.current.scale.setScalar(progress.current); invalidate(); }
    if (desired.current && controls.current) {
      const alpha = reduced ? 1 : 1 - Math.exp(-delta * 5);
      // Travel around the sphere rather than through it when focusing a rear node.
      const offset = camera.position.clone().sub(controls.current.target);
      const destination = desired.current.position.clone().sub(desired.current.target);
      const turn = new THREE.Quaternion().setFromUnitVectors(offset.clone().normalize(), destination.clone().normalize());
      offset.applyQuaternion(new THREE.Quaternion().slerp(turn, alpha)).setLength(THREE.MathUtils.lerp(offset.length(), destination.length(), alpha));
      controls.current.target.lerp(desired.current.target, alpha);
      camera.position.copy(controls.current.target).add(offset); controls.current.update(); invalidate();
      if (camera.position.distanceTo(desired.current.position) < .005) { desired.current = null; setMoving(false); }
    }
  });
  function pick(event: ThreeEvent<PointerEvent | MouseEvent>, hover = false) {
    event.stopPropagation(); if (event.instanceId === undefined) return;
    const node = result.graph_data.nodes[event.instanceId];
    if (node && visible.has(node.id)) { if (hover) onHover(node.id); else onSelect(node.id); }
  }
  const label = result.graph_data.nodes.find(n => n.id === (hoveredId || selectedId));
  return <>
    <group ref={assembly}>
      <LightScaffold positions={positions} enabled={!path.nodeIds.size && visible.size === result.graph_data.nodes.length}/>
      <mesh geometry={edgeGlow} raycast={() => null}><meshBasicMaterial color="#78dfff" transparent opacity={.16} blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false}/></mesh>
      <NodeHalos result={result} positions={positions} visible={visible} path={path.nodeIds} animate={animate}/>
      {result.graph_data.nodes.filter(n => n.type === 'IDENTITY' && visible.has(n.id)).map(n => <CentralFlare key={n.id} position={positions.get(n.id)!}/>) }
      <lineSegments geometry={edges} raycast={() => null}><lineBasicMaterial vertexColors transparent opacity={.85} toneMapped={false}/></lineSegments>
      <instancedMesh ref={mesh} args={[undefined, undefined, result.graph_data.nodes.length]} onPointerOver={e => pick(e, true)} onPointerMove={e => pick(e, true)} onPointerOut={() => onHover(null)} onClick={e => pick(e)}><sphereGeometry args={[1, 16, 12]}/><meshBasicMaterial toneMapped={false}/></instancedMesh>
      {result.graph_data.nodes.filter(n => n.status === 'ISSUE' && visible.has(n.id) && (!path.nodeIds.size || path.nodeIds.has(n.id))).map(n => <AlertRing key={n.id} position={positions.get(n.id)!} animate={animate} phase={n.id.length + positions.get(n.id)![0]}/>)}
      {flowCurves.map(({ edge, curve }) => <FlowParticle key={edge.id} curve={curve} animate={animate && visible.has(edge.source) && visible.has(edge.target)}/>)}
      {label && <Html position={positions.get(label.id)!} center zIndexRange={[7, 1]} style={{ pointerEvents: 'none', transform: 'translateY(-36px)' }}><div className={`globe-tooltip ${label.status === 'ISSUE' ? 'alert' : ''}`}>{label.status === 'ISSUE' && <span>!</span>}{label.label}<small>{label.status.toLowerCase()}</small></div></Html>}
    </group>
    <OrbitControls ref={controls} makeDefault enablePan={false} minDistance={4} maxDistance={14} autoRotate={animate && !selectedId && !hoveredId && !moving} autoRotateSpeed={.5} enableDamping={!reduced} dampingFactor={.08} onStart={() => { performance.regress(); desired.current = null; setMoving(false); }} onChange={() => invalidate()}/><AdaptiveDpr/>
  </>;
}
/** Ambient geometry is never pickable, counted or used for investigation paths. */
function LightScaffold({ positions, enabled }: { positions: Map<string, [number, number, number]>; enabled: boolean }) {
  const geometry = useMemo(() => {
    const points = [...positions.values()].filter(p => Math.hypot(...p) > 1);
    const verts: number[] = [], pairs = new Set<string>();
    points.forEach((a, i) => {
      points.map((b, j) => ({ b, j, d: Math.hypot(...a.map((v, k) => v - b[k])) })).filter(p => p.j !== i).sort((a,b) => a.d-b.d).slice(0,3).forEach(({b,j}) => {
        const key = [Math.min(i,j),Math.max(i,j)].join(':');
        if (!pairs.has(key)) { pairs.add(key); verts.push(...a,...b); }
      });
    });
    return new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(verts,3));
  }, [positions]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  const rays = useMemo(() => {
    const center = [...positions.values()].find(p => Math.hypot(...p) < 1);
    const verts: number[] = [];
    if (center) [...positions.values()].filter(p => Math.hypot(...p) > 1).forEach((p,i) => { if(i % 2 === 0) verts.push(...center,...p); });
    return new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(verts,3));
  }, [positions]);
  useEffect(() => () => rays.dispose(), [rays]);
  return <group visible={enabled}><lineSegments geometry={geometry} raycast={() => null}><lineBasicMaterial color="#46d9ff" transparent opacity={.32} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false}/></lineSegments><lineSegments geometry={rays} raycast={() => null}><lineBasicMaterial color="#ffd1f5" transparent opacity={.27} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false}/></lineSegments></group>;
}
function CentralFlare({ position }: { position: [number, number, number] }) {
  return <Billboard position={position}><mesh raycast={() => null}><planeGeometry args={[2.1,2.1]}/><shaderMaterial transparent depthWrite={false} depthTest={false} blending={THREE.AdditiveBlending}
    vertexShader={`varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`}
    fragmentShader={`varying vec2 vUv; void main(){vec2 p=vUv-.5;float r=length(p);float a=atan(p.y,p.x);float rays=pow(abs(cos(a*4.)),32.)*exp(-r*14.);float glow=exp(-r*r*65.);float core=exp(-r*r*2800.);gl_FragColor=vec4(mix(vec3(1.,.65,.92),vec3(1.),core),glow*.65+rays*1.5+core);}`}/></mesh></Billboard>;
}
function NodeHalos({ result, positions, visible, path, animate }: { result: CaseResult; positions: Map<string, [number, number, number]>; visible: Set<string>; path: Set<string>; animate: boolean }) {
  const material = useRef<THREE.ShaderMaterial>(null);
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry(), coords: number[] = [], colors: number[] = [], sizes: number[] = [], phases: number[] = [], periods: number[] = [];
    result.graph_data.nodes.forEach((n, i) => {
      coords.push(...positions.get(n.id)!);
      const dim = !visible.has(n.id) || (path.size > 0 && !path.has(n.id));
      colors.push(...new THREE.Color(n.type === 'IDENTITY' ? '#ffc5ef' : n.status === 'VERIFIED' ? '#4af3df' : nodeColors[n.status]).multiplyScalar(dim ? .03 : 1).toArray());
      const hub = ['IDENTITY', 'SYSTEM', 'BACKUP'].includes(n.type);
      sizes.push(n.type === 'IDENTITY' ? 230 : hub || n.status === 'ISSUE' ? 135 : 90); phases.push(i * 2.399);
      periods.push(n.status === 'ISSUE' ? 3 : (hub ? 5 : 4) + (i % 7) / 2);
    });
    g.setAttribute('position', new THREE.Float32BufferAttribute(coords, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    g.setAttribute('aSize', new THREE.Float32BufferAttribute(sizes, 1));
    g.setAttribute('aPhase', new THREE.Float32BufferAttribute(phases, 1));
    g.setAttribute('aPeriod', new THREE.Float32BufferAttribute(periods, 1));
    return g;
  }, [result, positions, visible, path]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  const uniforms = useMemo(() => ({ time: { value: 0 } }), []);
  useFrame((_, delta) => { if (animate && material.current) material.current.uniforms.time.value += delta; });
  return <points geometry={geometry} raycast={() => null}><shaderMaterial ref={material} uniforms={uniforms} transparent depthWrite={false} depthTest={false} vertexColors blending={THREE.AdditiveBlending}
    vertexShader={`attribute float aSize; attribute float aPhase; attribute float aPeriod;
      uniform float time; varying vec3 glowColor; varying float pulse;
      void main(){glowColor=color; pulse=.72+.28*sin(time*6.283185/aPeriod+aPhase);
      vec4 mv=modelViewMatrix*vec4(position,1.); gl_Position=projectionMatrix*mv;
      gl_PointSize=clamp(aSize*8./-mv.z,2.,260.);}`}
    fragmentShader={`varying vec3 glowColor; varying float pulse;
      void main(){float r=length(gl_PointCoord-.5)*2.; if(r>1.) discard;
      float alpha=(exp(-r*r*12.)*.95+pow(1.-r,4.)*.9)*pulse; gl_FragColor=vec4(glowColor,alpha);
#include <colorspace_fragment>
}`}/></points>;
}
function AlertRing({ position, animate, phase }: { position: [number, number, number]; animate: boolean; phase: number }) {
  const ring = useRef<THREE.Mesh>(null), t = useRef(0);
  useFrame((_, delta) => { if (animate && ring.current) { t.current += delta; ring.current.scale.setScalar(1 + Math.sin(t.current * (Math.PI * 2 / 3) + phase) * .12); } });
  return <Billboard position={position}><mesh ref={ring} raycast={() => null}><ringGeometry args={[.145, .158, 40]}/><meshBasicMaterial color="#ff435e" side={THREE.DoubleSide} transparent opacity={.6} depthWrite={false}/></mesh><mesh position={[.13, .13, .01]} raycast={() => null}><circleGeometry args={[.035, 3]}/><meshBasicMaterial color="#ff435e" side={THREE.DoubleSide}/></mesh></Billboard>;
}
function FlowParticle({ curve, animate }: { curve: THREE.QuadraticBezierCurve3; animate: boolean }) {
  const particle = useRef<THREE.Mesh>(null), elapsed = useRef(.15);
  useFrame((_, delta) => { if (animate) elapsed.current += delta * .14; if (particle.current) particle.current.position.copy(curve.getPoint(elapsed.current % 1)); });
  return <mesh ref={particle} raycast={() => null}><sphereGeometry args={[.032, 8, 8]}/><meshBasicMaterial color="#c8e5ff"/></mesh>;
}
export default function GlobeScene(props: Props) {
  return <Canvas camera={{ position: home.toArray(), fov: 44 }} dpr={[1, 1.6]} frameloop={props.animate ? 'always' : 'demand'} gl={{ alpha: true, antialias: true, powerPreference: 'low-power' }} onCreated={({ gl }) => { gl.setClearColor(0xffffff, 0); gl.domElement.addEventListener('webglcontextlost', props.onContextLost, { once: true }); }}><Network {...props}/></Canvas>;
}
