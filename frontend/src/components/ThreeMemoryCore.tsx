import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface ThreeMemoryCoreProps {
  glowColor: string
  providerName: string
}

export default function ThreeMemoryCore({ glowColor, providerName }: ThreeMemoryCoreProps) {
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    const width = container.clientWidth || 600
    const height = container.clientHeight || 340

    // 1. Scene & Camera
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    camera.position.z = 5.2

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    container.appendChild(renderer.domElement)

    // 3. Colors
    const primaryColor = new THREE.Color(glowColor || '#a855f7')
    const accentColor = new THREE.Color('#22d3ee')

    // 4. Central Group
    const coreGroup = new THREE.Group()
    scene.add(coreGroup)

    // A. Inner Crystalline Icosahedron (Glowing Core)
    const innerGeo = new THREE.IcosahedronGeometry(1.0, 1)
    const innerMat = new THREE.MeshBasicMaterial({
      color: primaryColor,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    })
    const innerMesh = new THREE.Mesh(innerGeo, innerMat)
    coreGroup.add(innerMesh)

    // B. Inner Solid Core (pulsing energy crystal)
    const solidGeo = new THREE.OctahedronGeometry(0.55, 0)
    const solidMat = new THREE.MeshBasicMaterial({
      color: accentColor,
      wireframe: false,
      transparent: true,
      opacity: 0.18,
    })
    const solidMesh = new THREE.Mesh(solidGeo, solidMat)
    coreGroup.add(solidMesh)

    // C. Glowing Node Vertices
    const vertexPointsGeo = new THREE.BufferGeometry()
    const pos = innerGeo.attributes.position.array
    vertexPointsGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const pointsMat = new THREE.PointsMaterial({
      color: primaryColor,
      size: 0.09,
      transparent: true,
      opacity: 0.9,
    })
    const vertexPoints = new THREE.Points(vertexPointsGeo, pointsMat)
    coreGroup.add(vertexPoints)

    // D. Outer Gyroscopic / Orbital Rings
    const ringGroup = new THREE.Group()
    coreGroup.add(ringGroup)

    const createRing = (radius: number, tiltX: number, tiltY: number, color: THREE.Color) => {
      const ringGeo = new THREE.TorusGeometry(radius, 0.014, 16, 100)
      const ringMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.4,
      })
      const ringMesh = new THREE.Mesh(ringGeo, ringMat)
      ringMesh.rotation.x = tiltX
      ringMesh.rotation.y = tiltY

      // Energy Bead on the ring
      const beadGeo = new THREE.SphereGeometry(0.06, 16, 16)
      const beadMat = new THREE.MeshBasicMaterial({ color: 0xffffff })
      const bead = new THREE.Mesh(beadGeo, beadMat)
      ringMesh.add(bead)

      return { ringMesh, bead, radius }
    }

    const ring1 = createRing(1.6, Math.PI / 3, Math.PI / 6, primaryColor)
    const ring2 = createRing(1.9, -Math.PI / 4, Math.PI / 4, accentColor)
    const ring3 = createRing(2.2, Math.PI / 5, -Math.PI / 3, primaryColor)

    ringGroup.add(ring1.ringMesh)
    ringGroup.add(ring2.ringMesh)
    ringGroup.add(ring3.ringMesh)

    // E. Ambient Floating Data Particles (Memory Starfield)
    const particleCount = 180
    const particleGeo = new THREE.BufferGeometry()
    const particlePositions = new Float32Array(particleCount * 3)

    for (let i = 0; i < particleCount; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(Math.random() * 2 - 1)
      const r = 1.6 + Math.random() * 1.8
      particlePositions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      particlePositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      particlePositions[i * 3 + 2] = r * Math.cos(phi)
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3))
    const particleMat = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.035,
      transparent: true,
      opacity: 0.6,
    })
    const particleField = new THREE.Points(particleGeo, particleMat)
    coreGroup.add(particleField)

    // 5. Mouse Parallax
    let targetX = 0
    let targetY = 0
    const onMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1)
      targetX = x * 0.45
      targetY = y * 0.35
    }

    window.addEventListener('mousemove', onMouseMove)

    // 6. Handle Resize
    const onResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    // 7. Animation Loop
    let animId: number
    let clock = new THREE.Clock()

    const animate = () => {
      animId = requestAnimationFrame(animate)
      const elapsedTime = clock.getElapsedTime()

      // Smooth inertia rotation from mouse
      coreGroup.rotation.y += (targetX - coreGroup.rotation.y) * 0.06
      coreGroup.rotation.x += (targetY - coreGroup.rotation.x) * 0.06

      // Idle continuous rotation
      innerMesh.rotation.y += 0.008
      innerMesh.rotation.x += 0.004

      solidMesh.rotation.y -= 0.012
      solidMesh.rotation.z += 0.006

      // Breathing pulse on inner core
      const pulse = 1 + Math.sin(elapsedTime * 2.5) * 0.06
      innerMesh.scale.set(pulse, pulse, pulse)

      // Orbiting energy beads
      const t1 = elapsedTime * 1.8
      ring1.bead.position.set(Math.cos(t1) * ring1.radius, Math.sin(t1) * ring1.radius, 0)

      const t2 = -elapsedTime * 1.4
      ring2.bead.position.set(Math.cos(t2) * ring2.radius, Math.sin(t2) * ring2.radius, 0)

      const t3 = elapsedTime * 1.1
      ring3.bead.position.set(Math.cos(t3) * ring3.radius, Math.sin(t3) * ring3.radius, 0)

      // Slow gyroscopic drift
      ring1.ringMesh.rotation.z += 0.004
      ring2.ringMesh.rotation.z -= 0.005
      ring3.ringMesh.rotation.z += 0.003

      particleField.rotation.y += 0.0015

      renderer.render(scene, camera)
    }

    animate()

    // 8. Cleanup
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('resize', onResize)
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
      renderer.dispose()
      innerGeo.dispose()
      innerMat.dispose()
      solidGeo.dispose()
      solidMat.dispose()
      vertexPointsGeo.dispose()
      pointsMat.dispose()
      particleGeo.dispose()
      particleMat.dispose()
    }
  }, [glowColor, providerName])

  return (
    <div className="relative w-full h-full min-h-[300px] flex items-center justify-center overflow-hidden">
      {/* Background ambient radial glow matching provider */}
      <div
        className="absolute w-[280px] h-[280px] rounded-full blur-[80px] pointer-events-none transition-all duration-700 opacity-60"
        style={{
          background: `radial-gradient(circle, ${glowColor}55 0%, rgba(34,211,238,0.2) 60%, transparent 80%)`,
        }}
      />
      {/* Three.js canvas mount container */}
      <div ref={mountRef} className="w-full h-full absolute inset-0 cursor-grab active:cursor-grabbing" />
    </div>
  )
}
