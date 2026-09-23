import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line, Sphere, Billboard, Text } from '@react-three/drei';
import * as THREE from 'three';

interface ApplicableLaw {
  article: string;
  document: string;
  title: string;
  relevance_score: number;
}

interface RelatedCase {
  title?: string;
  citation?: string;
  relevance_score?: number;
  outcome?: string;
}

interface EvidenceItem {
  label: string;
  status: string; // 'present', 'missing', etc.
}

interface CaseLawGraphProps {
  laws: ApplicableLaw[];
  cases: RelatedCase[];
  checklist?: EvidenceItem[];
  label?: string;
}

const COLORS = {
  center: '#002045',
  law: '#28657a',
  case: '#059669',
  edge: '#c4c6cf',
};

const GraphScene = ({ laws, cases, label }: any) => {
  const groupRef = useRef<THREE.Group>(null);
  
  useFrame((_state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.1;
    }
  });

  const centerPos = new THREE.Vector3(0, 0, 0);

  // Position nodes radially
  const lawNodes = useMemo(() => {
    return laws.map((law: any, i: number) => {
      const angle = (i / Math.max(1, laws.length)) * Math.PI * 2;
      const radius = 3;
      return {
        pos: new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 1.5),
        label: law.article,
      };
    });
  }, [laws]);

  const caseNodes = useMemo(() => {
    return cases.map((c: any, i: number) => {
      const angle = (i / Math.max(1, cases.length)) * Math.PI * 2 + Math.PI / 4;
      const radius = 4;
      return {
        pos: new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, -1.5),
        label: (c.title || c.citation || '').slice(0, 15) + '...',
      };
    });
  }, [cases]);

  return (
    <group ref={groupRef}>
      {/* Center Node */}
      <Sphere args={[0.5, 32, 32]} position={centerPos}>
        <meshPhysicalMaterial color={COLORS.center} emissive={COLORS.center} emissiveIntensity={0.3} roughness={0.2} metalness={0.8} clearcoat={1.0} clearcoatRoughness={0.1} />
      </Sphere>
      <Billboard position={[0, -0.8, 0]}>
        <Text fontSize={0.265} color={COLORS.center} anchorX="center" anchorY="middle" outlineWidth={0.02} outlineColor="#fff" fillOpacity={0.9}>
          {label}
        </Text>
      </Billboard>

      {/* Law Nodes */}
      {lawNodes.map((node: any, i: number) => (
        <group key={`law-${i}`}>
          <Line points={[centerPos, node.pos]} color={COLORS.law} lineWidth={2} transparent opacity={0.5} />
          <Sphere args={[0.3, 32, 32]} position={node.pos}>
            <meshPhysicalMaterial color={COLORS.law} emissive={COLORS.law} emissiveIntensity={0.1} roughness={0.2} metalness={0.5} clearcoat={0.8} />
          </Sphere>
          <Billboard position={[node.pos.x, node.pos.y - 0.5, node.pos.z]}>
            <Text fontSize={0.21} color={COLORS.law} outlineWidth={0.02} outlineColor="#fff" fillOpacity={0.9}>
              {node.label}
            </Text>
          </Billboard>
        </group>
      ))}

      {/* Case Nodes */}
      {caseNodes.map((node: any, i: number) => (
        <group key={`case-${i}`}>
          <Line points={[centerPos, node.pos]} color={COLORS.case} lineWidth={1.5} transparent opacity={0.4} />
          <Sphere args={[0.25, 32, 32]} position={node.pos}>
            <meshPhysicalMaterial color={COLORS.case} emissive={COLORS.case} emissiveIntensity={0.1} roughness={0.3} metalness={0.4} clearcoat={0.5} />
          </Sphere>
          <Billboard position={[node.pos.x, node.pos.y - 0.4, node.pos.z]}>
            <Text fontSize={0.16} color={COLORS.case} outlineWidth={0.02} outlineColor="#fff" fillOpacity={0.9}>
              {node.label}
            </Text>
          </Billboard>
        </group>
      ))}
    </group>
  );
};

export const CaseLawGraph: React.FC<CaseLawGraphProps> = ({ laws, cases, label = 'Case Narrative' }) => {
  return (
    <div className="w-full h-full rounded-2xl overflow-hidden relative cursor-move bg-gradient-to-br from-[#f8f9ff] via-[#eff4ff] to-[#dce9ff]">
      {/* Decorative ambient blurred orbs for glassmorphic depth */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-gradient-to-br from-[#adc7f7] to-[#28657a] opacity-10 blur-[80px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-gradient-to-tl from-[#abe5fe] to-transparent opacity-20 blur-[100px] pointer-events-none" />
      
      <Canvas camera={{ position: [0, 4, 8], fov: 50 }}>
        {/* Environment and Lighting */}
        <ambientLight intensity={0.7} color="#ffffff" />
        <directionalLight position={[10, 20, 10]} intensity={1.5} color="#ffffff" />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#abe5fe" />
        <pointLight position={[0, 5, 5]} intensity={1.2} color="#eff4ff" />

        <GraphScene laws={laws} cases={cases} label={label} />
        <OrbitControls enableZoom={true} autoRotate autoRotateSpeed={0.8} dampingFactor={0.05} />
      </Canvas>
    </div>
  );
};
