import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';

export default function Vehicle3DViewer({
  label = "Véhicule A",
  vehicleType = 1, // 1: Car/Tesla, 2: Moto, 3: Velo, 10: Trottinette, 4/5/8: Truck, 6/7: Bus
  selectedImpact = null,
  onImpactSelect,
}) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const vehicleGroupRef = useRef(null);
  const zonesRef = useRef({});
  const shockwaveGroupRef = useRef(null);

  const [activeZone, setActiveZone] = useState(selectedImpact || 'front');
  const [animatingWave, setAnimatingWave] = useState(false);

  useEffect(() => {
    if (selectedImpact && selectedImpact !== activeZone) {
      setActiveZone(selectedImpact);
      highlightZone(selectedImpact);
    }
  }, [selectedImpact]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 340;
    const height = 240; // Hauteur agrandie pour une excellente lisibilité

    // 1. Scène
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x0a0f1d);

    // 2. Caméra
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(5.2, 3.4, 6.2);
    camera.lookAt(0, 0.6, 0);
    cameraRef.current = camera;

    // 3. Renderer WebGL
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    rendererRef.current = renderer;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 4. Lumières studio
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
    keyLight.position.set(7, 10, 7);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.7);
    fillLight.position.set(-6, 5, -6);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xef4444, 0.4);
    rimLight.position.set(0, -3, -5);
    scene.add(rimLight);

    // 5. Grille tactique de sol
    const gridHelper = new THREE.GridHelper(10, 20, 0x3b82f6, 0x1e293b);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // 6. Groupes
    const vehicleGroup = new THREE.Group();
    scene.add(vehicleGroup);
    vehicleGroupRef.current = vehicleGroup;

    const shockwaveGroup = new THREE.Group();
    scene.add(shockwaveGroup);
    shockwaveGroupRef.current = shockwaveGroup;

    // Construction procédurale du modèle
    buildVehicleGeometry(vehicleGroup, vehicleType);

    // 7. Interaction souris : Rotation Orbitale
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    const handleMouseDown = (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      vehicleGroup.rotation.y += deltaX * 0.015;
      camera.position.y = Math.max(1.0, Math.min(7.0, camera.position.y + deltaY * 0.02));
      camera.lookAt(0, 0.6, 0);

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDragging = false;
    };

    // Zoom & Dézoom avec la molette de la souris
    const handleWheel = (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY * 0.004;
      const dist = camera.position.length();
      const newDist = Math.max(2.2, Math.min(11.0, dist + zoomFactor));
      camera.position.setLength(newDist);
      camera.lookAt(0, 0.6, 0);
    };

    // 8. Raycasting : Clic sur zone d'impact
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handleClick = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const meshes = Object.values(zonesRef.current);
      const intersects = raycaster.intersectObjects(meshes, true);

      if (intersects.length > 0) {
        const hitObject = intersects[0].object;
        const zoneKey = hitObject.userData.zoneKey;
        const hitPoint = intersects[0].point;

        if (zoneKey) {
          triggerShockwave(hitPoint);
          selectZone(zoneKey);
        }
      }
    };

    const dom = renderer.domElement;
    dom.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    dom.addEventListener('wheel', handleWheel, { passive: false });
    dom.addEventListener('click', handleClick);

    // 9. Boucle d'animation
    let reqId;
    const animate = () => {
      reqId = requestAnimationFrame(animate);

      if (shockwaveGroup.children.length > 0) {
        shockwaveGroup.children.forEach((wave) => {
          wave.scale.x += 0.08;
          wave.scale.y += 0.08;
          wave.scale.z += 0.08;
          wave.material.opacity -= 0.035;
          if (wave.material.opacity <= 0) {
            shockwaveGroup.remove(wave);
          }
        });
      }

      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth || 340;
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
      renderer.setSize(w, height);
    };
    window.addEventListener('resize', handleResize);

    // Observer pour ajuster automatiquement la taille dès que le conteneur flex/grid se stabilise
    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });
    resizeObserver.observe(container);

    // Timeout de sécurité pour recentrer après le rendu React conditionnel
    const autoResizeTimer = setTimeout(() => {
      handleResize();
    }, 120);

    return () => {
      cancelAnimationFrame(reqId);
      clearTimeout(autoResizeTimer);
      resizeObserver.disconnect();
      dom.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      dom.removeEventListener('wheel', handleWheel);
      dom.removeEventListener('click', handleClick);
      window.removeEventListener('resize', handleResize);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [vehicleType]);

  // Construction procédurale selon le type de véhicule
  const buildVehicleGeometry = (group, type) => {
    zonesRef.current = {};
    group.clear();

    const bodyPaint = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.7,
      roughness: 0.3,
    });
    const glassMaterial = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      metalness: 0.9,
      roughness: 0.1,
      transparent: true,
      opacity: 0.65,
    });
    const rubberMaterial = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.85,
    });
    const rimMaterial = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      metalness: 0.9,
      roughness: 0.2,
    });
    const ledWhite = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const ledRed = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const chrome = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.95, roughness: 0.1 });

    const code = Number(type);

    if (code === 2) {
      // --- 1. MOTO SPORTIVE RÉALISTE ---
      // Cadre tubulaire incliné
      const frameGeo = new THREE.CylinderGeometry(0.08, 0.08, 1.6, 8);
      frameGeo.rotateZ(Math.PI / 4);
      const frame = new THREE.Mesh(frameGeo, bodyPaint);
      frame.position.set(0, 0.75, 0);
      group.add(frame);

      // Réservoir profilé bombé
      const tankGeo = new THREE.SphereGeometry(0.35, 16, 16);
      tankGeo.scale(1.2, 0.8, 1.6);
      const tank = new THREE.Mesh(tankGeo, bodyPaint);
      tank.position.set(0, 0.95, 0.35);
      group.add(tank);

      // Selle profilée étagée
      const seatGeo = new THREE.BoxGeometry(0.32, 0.12, 0.7);
      const seat = new THREE.Mesh(seatGeo, rubberMaterial);
      seat.position.set(0, 0.85, -0.4);
      group.add(seat);

      // Fourche avant inclinée
      const forkGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.2, 8);
      forkGeo.rotateX(Math.PI / 6);
      const forkL = new THREE.Mesh(forkGeo, chrome);
      forkL.position.set(-0.12, 0.65, 0.85);
      const forkR = new THREE.Mesh(forkGeo, chrome);
      forkR.position.set(0.12, 0.65, 0.85);
      group.add(forkL, forkR);

      // Guidon avec poignées
      const barGeo = new THREE.BoxGeometry(0.75, 0.05, 0.06);
      const handlebar = new THREE.Mesh(barGeo, chrome);
      handlebar.position.set(0, 1.15, 0.65);
      group.add(handlebar);

      // Échappement chromé
      const exhaustGeo = new THREE.CylinderGeometry(0.07, 0.09, 1.0, 12);
      exhaustGeo.rotateX(Math.PI / 2.3);
      const exhaust = new THREE.Mesh(exhaustGeo, chrome);
      exhaust.position.set(0.24, 0.45, -0.6);
      group.add(exhaust);

      // Roues sportives avec jantes
      const createMotoWheel = (z) => {
        const wGroup = new THREE.Group();
        const tire = new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.09, 12, 24), rubberMaterial);
        const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.06, 12), rimMaterial);
        rim.rotateZ(Math.PI / 2);
        wGroup.add(tire, rim);
        wGroup.position.set(0, 0.4, z);
        return wGroup;
      };
      group.add(createMotoWheel(1.15), createMotoWheel(-1.05));

      // Zones d'impact moto
      createImpactZone(group, 'front', new THREE.BoxGeometry(0.7, 0.8, 0.7), [0, 0.75, 1.2], "Face Avant / Fourche");
      createImpactZone(group, 'rear', new THREE.BoxGeometry(0.7, 0.8, 0.7), [0, 0.75, -1.1], "Face Arrière / Roue");
      createImpactZone(group, 'left', new THREE.BoxGeometry(0.4, 0.8, 1.4), [-0.4, 0.75, 0], "Flanc Gauche");
      createImpactZone(group, 'right', new THREE.BoxGeometry(0.4, 0.8, 1.4), [0.4, 0.75, 0], "Flanc Droit");
      createImpactZone(group, 'roof', new THREE.BoxGeometry(0.6, 0.5, 0.8), [0, 1.25, 0.2], "Poste de conduite / Guidon");

    } else if (code === 3) {
      // --- 2. VÉLO / VAE (MOBILITÉ DOUCE) ---
      // Cadre diamant en tubes fins
      const bikeTubeMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.6, roughness: 0.3 });
      
      const createTube = (p1, p2, radius = 0.025) => {
        const v1 = new THREE.Vector3(...p1);
        const v2 = new THREE.Vector3(...p2);
        const dist = v1.distanceTo(v2);
        const geo = new THREE.CylinderGeometry(radius, radius, dist, 8);
        const mesh = new THREE.Mesh(geo, bikeTubeMat);
        mesh.position.copy(v1).add(v2).multiplyScalar(0.5);
        mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v2.clone().sub(v1).normalize());
        return mesh;
      };

      // Tubes du cadre
      group.add(createTube([0, 0.4, 0.8], [0, 0.95, 0.55]));  // Tube direction
      group.add(createTube([0, 0.95, 0.55], [0, 0.9, -0.2])); // Tube supérieur
      group.add(createTube([0, 0.95, 0.55], [0, 0.4, 0.0]));  // Tube diagonal
      group.add(createTube([0, 0.9, -0.2], [0, 0.4, 0.0]));   // Tube selle
      group.add(createTube([0, 0.4, 0.0], [0, 0.4, -0.8]));   // Bases arrières
      group.add(createTube([0, 0.9, -0.2], [0, 0.4, -0.8]));  // Haubans

      // Guidon & Selle
      const bikeBar = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.03, 0.04), chrome);
      bikeBar.position.set(0, 1.05, 0.52);
      const bikeSeat = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.06, 0.3), rubberMaterial);
      bikeSeat.position.set(0, 0.98, -0.2);
      group.add(bikeBar, bikeSeat);

      // Roues fines 28"
      const createBikeWheel = (z) => {
        const w = new THREE.Group();
        const tire = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.025, 8, 32), rubberMaterial);
        const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.08, 8), chrome);
        hub.rotateZ(Math.PI / 2);
        w.add(tire, hub);
        w.position.set(0, 0.42, z);
        return w;
      };
      group.add(createBikeWheel(0.8), createBikeWheel(-0.8));

      // Zones d'impact Vélo
      createImpactZone(group, 'front', new THREE.BoxGeometry(0.5, 0.8, 0.5), [0, 0.65, 0.85], "Roue Avant / Fourche");
      createImpactZone(group, 'rear', new THREE.BoxGeometry(0.5, 0.8, 0.5), [0, 0.65, -0.85], "Roue Arrière / Cadre");
      createImpactZone(group, 'left', new THREE.BoxGeometry(0.3, 0.8, 1.4), [-0.25, 0.65, 0], "Flanc Gauche");
      createImpactZone(group, 'right', new THREE.BoxGeometry(0.3, 0.8, 1.4), [0.25, 0.65, 0], "Flanc Droit");
      createImpactZone(group, 'roof', new THREE.BoxGeometry(0.5, 0.4, 0.6), [0, 1.1, 0.3], "Guidon / Selle");

    } else if (code === 10) {
      // --- 3. TROTTINETTE / EDPM ---
      // Plateau bas allongé
      const deckGeo = new THREE.BoxGeometry(0.24, 0.06, 1.1);
      const deck = new THREE.Mesh(deckGeo, rubberMaterial);
      deck.position.set(0, 0.16, -0.05);
      group.add(deck);

      // Colonne de direction verticale haute
      const poleGeo = new THREE.CylinderGeometry(0.03, 0.03, 1.05, 8);
      poleGeo.rotateX(-0.1);
      const pole = new THREE.Mesh(poleGeo, chrome);
      pole.position.set(0, 0.65, 0.46);
      group.add(pole);

      // Guidon en T
      const tBarGeo = new THREE.BoxGeometry(0.55, 0.04, 0.04);
      const tBar = new THREE.Mesh(tBarGeo, rubberMaterial);
      tBar.position.set(0, 1.18, 0.4);
      group.add(tBar);

      // Petites roues compactes
      const createScooterWheel = (z) => {
        const w = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.08, 16), rubberMaterial);
        w.rotateZ(Math.PI / 2);
        w.position.set(0, 0.12, z);
        return w;
      };
      group.add(createScooterWheel(0.5), createScooterWheel(-0.55));

      // Zones d'impact Trottinette
      createImpactZone(group, 'front', new THREE.BoxGeometry(0.4, 0.9, 0.4), [0, 0.6, 0.5], "Roue Avant / Colonne");
      createImpactZone(group, 'rear', new THREE.BoxGeometry(0.4, 0.5, 0.4), [0, 0.3, -0.55], "Roue Arrière / Frein");
      createImpactZone(group, 'left', new THREE.BoxGeometry(0.25, 0.8, 1.0), [-0.2, 0.5, 0], "Côté Gauche");
      createImpactZone(group, 'right', new THREE.BoxGeometry(0.25, 0.8, 1.0), [0.2, 0.5, 0], "Côté Droit");
      createImpactZone(group, 'roof', new THREE.BoxGeometry(0.5, 0.4, 0.4), [0, 1.2, 0.4], "Guidon T-Bar");

    } else if (code === 6 || code === 7) {
      // --- 4. TRANSPORT COLLECTIF / BUS & TRAMWAY ---
      const busLen = 4.8;
      const busWid = 1.6;
      const busHei = 1.6;

      // Caisse rectangulaire volumineuse
      const busGeo = new THREE.BoxGeometry(busWid, busHei * 0.7, busLen);
      const busBody = new THREE.Mesh(busGeo, bodyPaint);
      busBody.position.set(0, 0.3 + busHei * 0.35, 0);
      group.add(busBody);

      // Grandes baies vitrées panoramiques
      const glassBandGeo = new THREE.BoxGeometry(busWid + 0.02, busHei * 0.45, busLen * 0.94);
      const glassBand = new THREE.Mesh(glassBandGeo, glassMaterial);
      glassBand.position.set(0, 0.85, 0);
      group.add(glassBand);

      // Toit profilé avec climatiseurs
      const acUnit = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.18, 1.2), chrome);
      acUnit.position.set(0, 0.3 + busHei + 0.09, 0.5);
      group.add(acUnit);

      // Phares & Feux
      const fLight = new THREE.Mesh(new THREE.BoxGeometry(busWid * 0.8, 0.08, 0.05), ledWhite);
      fLight.position.set(0, 0.45, busLen / 2 + 0.01);
      const rLight = new THREE.Mesh(new THREE.BoxGeometry(busWid * 0.8, 0.08, 0.05), ledRed);
      rLight.position.set(0, 0.45, -busLen / 2 - 0.01);
      group.add(fLight, rLight);

      // Roues carénées
      const createBusWheel = (x, z) => {
        const w = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.24, 16), rubberMaterial);
        w.rotateZ(Math.PI / 2);
        w.position.set(x, 0.32, z);
        return w;
      };
      const bX = busWid / 2 + 0.04;
      group.add(
        createBusWheel(bX, 1.4), createBusWheel(-bX, 1.4),
        createBusWheel(bX, -1.4), createBusWheel(-bX, -1.4)
      );

      // Zones d'impact Bus
      createImpactZone(group, 'front', new THREE.BoxGeometry(busWid, 1.2, 0.6), [0, 0.9, busLen / 2], "Face Avant Bus");
      createImpactZone(group, 'rear', new THREE.BoxGeometry(busWid, 1.2, 0.6), [0, 0.9, -busLen / 2], "Face Arrière Bus");
      createImpactZone(group, 'left', new THREE.BoxGeometry(0.4, 1.2, busLen * 0.65), [-busWid / 2, 0.9, 0], "Flanc Gauche");
      createImpactZone(group, 'right', new THREE.BoxGeometry(0.4, 1.2, busLen * 0.65), [busWid / 2, 0.9, 0], "Flanc Droit");
      createImpactZone(group, 'left_front', new THREE.BoxGeometry(0.45, 1.0, 0.8), [-busWid / 2, 0.9, busLen / 2 - 0.5], "Flanc Av. Gauche");
      createImpactZone(group, 'right_front', new THREE.BoxGeometry(0.45, 1.0, 0.8), [busWid / 2, 0.9, busLen / 2 - 0.5], "Flanc Av. Droit");
      createImpactZone(group, 'roof', new THREE.BoxGeometry(busWid * 0.9, 0.4, busLen * 0.7), [0, busHei + 0.4, 0], "Dessus");

    } else if (code === 4 || code === 5 || code === 8) {
      // --- 5. POIDS LOURD / CAMION ---
      const cabLen = 1.4;
      const cabWid = 1.6;
      const cabHei = 1.6;
      const trailLen = 3.2;

      // Cabine avancée
      const cabGeo = new THREE.BoxGeometry(cabWid, cabHei, cabLen);
      const cab = new THREE.Mesh(cabGeo, bodyPaint);
      cab.position.set(0, 0.4 + cabHei / 2, 1.2);
      group.add(cab);

      // Pare-brise cabine
      const wShield = new THREE.Mesh(new THREE.BoxGeometry(cabWid * 0.95, 0.65, 0.1), glassMaterial);
      wShield.position.set(0, 1.4, 1.2 + cabLen / 2 + 0.02);
      group.add(wShield);

      // Déflecteur de toit aérodynamique
      const deflGeo = new THREE.ConeGeometry(0.8, 0.5, 4);
      deflGeo.rotateY(Math.PI / 4);
      const defl = new THREE.Mesh(deflGeo, bodyPaint);
      defl.position.set(0, 0.4 + cabHei + 0.25, 1.1);
      group.add(defl);

      // Grande caisse remorque arrière
      const trailGeo = new THREE.BoxGeometry(cabWid * 1.05, cabHei * 1.1, trailLen);
      const trailer = new THREE.Mesh(trailGeo, new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.5 }));
      trailer.position.set(0, 0.4 + cabHei * 0.55, -1.2);
      group.add(trailer);

      // Roues camion (cabine + double essieu remorque)
      const createTruckWheel = (x, z) => {
        const w = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.24, 16), rubberMaterial);
        w.rotateZ(Math.PI / 2);
        w.position.set(x, 0.36, z);
        return w;
      };
      const tX = cabWid / 2 + 0.05;
      group.add(
        createTruckWheel(tX, 1.2), createTruckWheel(-tX, 1.2),
        createTruckWheel(tX, -1.6), createTruckWheel(-tX, -1.6),
        createTruckWheel(tX, -2.4), createTruckWheel(-tX, -2.4)
      );

      // Zones d'impact Poids Lourd
      createImpactZone(group, 'front', new THREE.BoxGeometry(cabWid, 1.2, 0.5), [0, 1.1, 1.2 + cabLen / 2], "Face Avant Cabine");
      createImpactZone(group, 'rear', new THREE.BoxGeometry(cabWid, 1.2, 0.5), [0, 1.1, -1.2 - trailLen / 2], "Face Arrière Remorque");
      createImpactZone(group, 'left', new THREE.BoxGeometry(0.4, 1.2, trailLen), [-cabWid / 2, 1.1, -1.2], "Côté Gauche Remorque");
      createImpactZone(group, 'right', new THREE.BoxGeometry(0.4, 1.2, trailLen), [cabWid / 2, 1.1, -1.2], "Côté Droit Remorque");
      createImpactZone(group, 'left_front', new THREE.BoxGeometry(0.4, 1.1, 0.7), [-cabWid / 2, 1.1, 1.3], "Flanc Av. Gauche Cabine");
      createImpactZone(group, 'right_front', new THREE.BoxGeometry(0.4, 1.1, 0.7), [cabWid / 2, 1.1, 1.3], "Flanc Av. Droit Cabine");
      createImpactZone(group, 'roof', new THREE.BoxGeometry(cabWid, 0.5, 1.2), [0, cabHei + 0.6, 1.1], "Dessus");

    } else {
      // --- 6. VÉHICULE LÉGER / SUV MODERNE (TYPE TESLA MODEL Y) ---
      const carLen = 3.6;
      const carWid = 1.55;

      // Châssis bas profilé aérodynamique
      const lowerGeo = new THREE.BoxGeometry(carWid * 0.95, 0.35, carLen * 0.95);
      const lowerBody = new THREE.Mesh(lowerGeo, bodyPaint);
      lowerBody.position.y = 0.38;
      group.add(lowerBody);

      // Capot plongeant avant profilé
      const hoodGeo = new THREE.BoxGeometry(carWid * 0.9, 0.22, 1.0);
      const hood = new THREE.Mesh(hoodGeo, bodyPaint);
      hood.position.set(0, 0.58, 1.1);
      hood.rotateX(-0.1);
      group.add(hood);

      // Pavillon / Toit panoramique galbé en verre fumé type Model Y
      const roofGeo = new THREE.CylinderGeometry(carWid * 0.44, carWid * 0.48, 1.8, 16);
      roofGeo.rotateZ(Math.PI / 2);
      roofGeo.scale(1.0, 0.75, 1.1);
      const roof = new THREE.Mesh(roofGeo, glassMaterial);
      roof.position.set(0, 0.92, -0.1);
      group.add(roof);

      // Hayon arrière fuyant fastback
      const rearGeo = new THREE.BoxGeometry(carWid * 0.9, 0.28, 0.8);
      const rearHatch = new THREE.Mesh(rearGeo, bodyPaint);
      rearHatch.position.set(0, 0.65, -1.2);
      rearHatch.rotateX(0.2);
      group.add(rearHatch);

      // Bandeau de phares LED avant effilés
      const fLed = new THREE.Mesh(new THREE.BoxGeometry(carWid * 0.85, 0.05, 0.05), ledWhite);
      fLed.position.set(0, 0.55, carLen / 2 + 0.01);
      group.add(fLed);

      // Bandeau lumineux arrière rouge
      const rLed = new THREE.Mesh(new THREE.BoxGeometry(carWid * 0.85, 0.05, 0.05), ledRed);
      rLed.position.set(0, 0.65, -carLen / 2 - 0.01);
      group.add(rLed);

      // 4 roues sport avec jantes à branches
      const createCarWheel = (x, z) => {
        const wGroup = new THREE.Group();
        const tire = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.08, 12, 24), rubberMaterial);
        const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.12, 12), rimMaterial);
        rim.rotateZ(Math.PI / 2);
        wGroup.add(tire, rim);
        wGroup.position.set(x, 0.32, z);
        return wGroup;
      };

      const wX = carWid / 2 + 0.04;
      group.add(
        createCarWheel(wX, 1.05), createCarWheel(-wX, 1.05),
        createCarWheel(wX, -1.05), createCarWheel(-wX, -1.05)
      );

      // Zones d'impact Tesla Model Y
      createImpactZone(group, 'front', new THREE.BoxGeometry(carWid, 0.6, 0.6), [0, 0.55, carLen / 2], "Face Avant");
      createImpactZone(group, 'rear', new THREE.BoxGeometry(carWid, 0.6, 0.6), [0, 0.6, -carLen / 2], "Face Arrière / Coffre");
      createImpactZone(group, 'left', new THREE.BoxGeometry(0.35, 0.65, carLen * 0.5), [-carWid / 2, 0.65, 0], "Côté Gauche");
      createImpactZone(group, 'right', new THREE.BoxGeometry(0.35, 0.65, carLen * 0.5), [carWid / 2, 0.65, 0], "Côté Droit");
      createImpactZone(group, 'left_front', new THREE.BoxGeometry(0.4, 0.6, 0.7), [-carWid / 2, 0.6, carLen / 2 - 0.4], "Flanc Av. Gauche");
      createImpactZone(group, 'right_front', new THREE.BoxGeometry(0.4, 0.6, 0.7), [carWid / 2, 0.6, carLen / 2 - 0.4], "Flanc Av. Droit");
      createImpactZone(group, 'roof', new THREE.BoxGeometry(carWid * 0.8, 0.3, carLen * 0.55), [0, 1.15, 0], "Dessus");
    }

    highlightZone(activeZone);
  };

  const createImpactZone = (group, key, geometry, position, title) => {
    const mat = new THREE.MeshStandardMaterial({
      color: 0x475569,
      transparent: true,
      opacity: 0.35,
      roughness: 0.3,
      metalness: 0.1,
    });
    const mesh = new THREE.Mesh(geometry, mat);
    mesh.position.set(...position);
    mesh.userData = { zoneKey: key, title };
    group.add(mesh);
    zonesRef.current[key] = mesh;
  };

  const highlightZone = (zoneKey) => {
    Object.entries(zonesRef.current).forEach(([k, mesh]) => {
      if (k === zoneKey) {
        mesh.material.color.setHex(0xef4444); // Rouge d'alerte vif
        mesh.material.opacity = 0.85;
        mesh.material.wireframe = false;
      } else {
        mesh.material.color.setHex(0x475569);
        mesh.material.opacity = 0.35;
        mesh.material.wireframe = false;
      }
    });
  };

  const triggerShockwave = (origin) => {
    if (!shockwaveGroupRef.current) return;
    setAnimatingWave(true);
    setTimeout(() => setAnimatingWave(false), 900);

    const waveGeo = new THREE.RingGeometry(0.1, 0.28, 24);
    const waveMat = new THREE.MeshBasicMaterial({
      color: 0xef4444,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    });
    const wave = new THREE.Mesh(waveGeo, waveMat);
    wave.position.copy(origin);
    wave.lookAt(origin.clone().add(new THREE.Vector3(0, 1, 0)));
    shockwaveGroupRef.current.add(wave);
  };

  const selectZone = (zoneKey) => {
    setActiveZone(zoneKey);
    highlightZone(zoneKey);

    let macroChoc = "Frontal";
    let chocCode = 1;

    if (zoneKey === 'front') {
      macroChoc = "Frontal"; chocCode = 1;
    } else if (zoneKey === 'rear') {
      macroChoc = "Arriere"; chocCode = 4;
    } else if (zoneKey === 'left' || zoneKey === 'left_front') {
      macroChoc = "Lateral"; chocCode = 8;
    } else if (zoneKey === 'right' || zoneKey === 'right_front') {
      macroChoc = "Lateral"; chocCode = 7;
    } else if (zoneKey === 'roof') {
      macroChoc = "Multiple"; chocCode = 9;
    }

    if (onImpactSelect) {
      onImpactSelect(zoneKey, macroChoc, chocCode);
    }
  };

  const setCameraView = (view) => {
    if (!cameraRef.current || !vehicleGroupRef.current) return;
    const cam = cameraRef.current;
    const grp = vehicleGroupRef.current;
    grp.rotation.y = 0;

    switch (view) {
      case 'front': cam.position.set(0, 1.2, 5.5); break;
      case 'rear': cam.position.set(0, 1.2, -5.5); break;
      case 'left': cam.position.set(-5.5, 1.2, 0); break;
      case 'right': cam.position.set(5.5, 1.2, 0); break;
      default: cam.position.set(5.2, 3.4, 6.2);
    }
    cam.lookAt(0, 0.6, 0);
  };

  const resetCameraView = () => {
    if (!cameraRef.current || !vehicleGroupRef.current) return;
    vehicleGroupRef.current.rotation.y = 0;
    cameraRef.current.position.set(5.2, 3.4, 6.2);
    cameraRef.current.lookAt(0, 0.6, 0);
  };

  const currentZoneTitle = zonesRef.current[activeZone]?.userData?.title || "Frontal";

  return (
    <div className="relative flex flex-col bg-slate-100 dark:bg-slate-900/90 border border-blue-500/40 rounded-xl p-2 overflow-hidden shadow-inner">
      {/* Header du visualiseur 3D */}
      <div className="flex items-center justify-between mb-1.5 z-10 px-1">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-ping" />
          <span className="text-xs font-black uppercase tracking-wider text-blue-600 dark:text-blue-400">
            {label} - Modélisation 3D
          </span>
        </div>
        <span className="text-[10px] text-slate-600 dark:text-slate-400 bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-300 dark:border-slate-700">
          Molette = Zoom • Clic = Choc
        </span>
      </div>

      {/* Raccourcis de caméra & recentrage */}
      <div className="absolute top-10 right-3 z-10 flex flex-col space-y-1 bg-white/80 dark:bg-slate-800/80 backdrop-blur-md p-1 rounded-lg border border-slate-300 dark:border-slate-700 shadow-md">
        <button
          type="button"
          onClick={() => setCameraView('front')}
          title="Face Avant"
          className="p-1 text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white hover:bg-blue-500/10 rounded transition"
        >
          <ArrowUp className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={() => setCameraView('rear')}
          title="Face Arrière"
          className="p-1 text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white hover:bg-blue-500/10 rounded transition"
        >
          <ArrowDown className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={() => setCameraView('left')}
          title="Côté Gauche"
          className="p-1 text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white hover:bg-blue-500/10 rounded transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={() => setCameraView('right')}
          title="Côté Droit"
          className="p-1 text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white hover:bg-blue-500/10 rounded transition"
        >
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={resetCameraView}
          title="Recentrer la vue"
          className="p-1 text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white hover:bg-blue-500/10 rounded transition"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Canvas Three.js agrandi */}
      <div
        ref={mountRef}
        className="w-full h-[240px] cursor-grab active:cursor-grabbing rounded-lg overflow-hidden"
      />

      {/* Badge du point d'impact actif */}
      <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-slate-200 dark:border-slate-800 text-xs px-1">
        <div className="flex items-center space-x-2">
          <span className="text-slate-500 dark:text-slate-400 text-[11px] font-medium">Point d'impact :</span>
          <span className="font-black text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-950/80 px-2 py-0.5 rounded border border-red-400/40 text-[11px] uppercase tracking-wide">
            {currentZoneTitle}
          </span>
        </div>
        {animatingWave && (
          <span className="text-[10px] text-red-600 dark:text-red-400 font-black animate-pulse">
            Onde de choc validée
          </span>
        )}
      </div>
    </div>
  );
}
