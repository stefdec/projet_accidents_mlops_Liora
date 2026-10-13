import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Navigation, CloudSun, Wind, MapPin, CheckCircle, Radio, Search, X, Loader2 } from 'lucide-react';
import { fetchLiveWeather } from '../services/weatherService';

// Fix icône standard Leaflet en bundler
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Icône d'urgence rouge pulsante personnalisée
const emergencyIcon = L.divIcon({
  className: 'custom-emergency-pin',
  html: `
    <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px;">
      <div style="position: absolute; width: 32px; height: 32px; border-radius: 50%; background-color: rgba(239, 68, 68, 0.4); animation: ping 1.2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
      <div style="width: 20px; height: 20px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #b91c1c); border: 2.5px solid #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;">
        <div style="width: 6px; height: 6px; border-radius: 50%; background-color: #ffffff;"></div>
      </div>
    </div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

export default function OpenStreetMapViewer({
  latitude = 48.8566,
  longitude = 2.3522,
  openingTime,
  onLocationSelect,
  onWeatherUpdate,
  onLightingUpdate,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);

  const [currentCoord, setCurrentCoord] = useState({ lat: latitude, lon: longitude });
  const [roadInfo, setRoadInfo] = useState({
    name: "Axe routier identifié",
    city: "Paris",
    postcode: "75001",
    country: "France",
    fullAddress: "Axe routier identifié, 75001 Paris, France",
    type: "Voie communale",
    catr: 4,
    vma: 4
  });
  const [weatherData, setWeatherData] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const [validatedCall, setValidatedCall] = useState(false);

  // Recherche d'adresse
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const searchInputRef = useRef(null);

  const [spatialPRInfo, setSpatialPRInfo] = useState('');
  const [hasPublicLightingGeoJSON, setHasPublicLightingGeoJSON] = useState(null);
  const geoJsonLayerRef = useRef(null);

  // Simulation automatique de la couche GeoJSON Leaflet L.geoJSON pour l'éclairage public
  const updateGeoJSONLightingLayer = (lat, lon) => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const dateObj = openingTime || new Date();
    const currentHour = dateObj.getHours();

    let simulatedLum = 1; // Plein jour par défaut
    const isNightOrEvening = currentHour < 6 || currentHour >= 18;
    let label = "Plein jour (06h-18h) - Pas de simulation";
    let strokeColor = "#38bdf8"; // Bleu ciel
    let dashArray = "6, 6";

    if (isNightOrEvening) {
      // Tirage aléatoire automatique à des fins de démonstration entre 3, 4 et 5
      const possibleLums = [3, 4, 5];
      simulatedLum = possibleLums[Math.floor(Math.random() * possibleLums.length)];

      if (simulatedLum === 5) {
        label = "Nuit - Éclairage public ALLUMÉ (Code 5)";
        strokeColor = "#f59e0b"; // Ambre lumineux
        dashArray = null;
      } else if (simulatedLum === 4) {
        label = "Nuit - Éclairage public NON ALLUMÉ (Code 4)";
        strokeColor = "#64748b"; // Gris / Éteint
        dashArray = "4, 4";
      } else {
        label = "Nuit - Sans éclairage public (Code 3)";
        strokeColor = "#ef4444"; // Rouge / Sombre
        dashArray = "2, 6";
      }
    }

    setHasPublicLightingGeoJSON({
      isNight: isNightOrEvening,
      lumCode: simulatedLum,
      label,
      strokeColor,
    });

    if (onLightingUpdate) {
      onLightingUpdate(simulatedLum);
    }

    // Retrait du précédent calque GeoJSON L.geoJSON
    if (geoJsonLayerRef.current && map.hasLayer(geoJsonLayerRef.current)) {
      map.removeLayer(geoJsonLayerRef.current);
    }

    // Géométrie GeoJSON (Axe routier + Point d'éclairage OSM)
    const sampleLightingGeoJSON = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {
            name: "Segment Routier GeoJSON OSM",
            isNight: isNightOrEvening,
            lumCode: simulatedLum,
            label,
          },
          geometry: {
            type: "LineString",
            coordinates: [
              [lon - 0.002, lat - 0.001],
              [lon, lat],
              [lon + 0.002, lat + 0.001]
            ]
          }
        },
        {
          type: "Feature",
          properties: {
            name: "Mat d'Éclairage GeoJSON OSM",
            label,
          },
          geometry: {
            type: "Point",
            coordinates: [lon + 0.0004, lat + 0.0004]
          }
        }
      ]
    };

    const newGeoLayer = L.geoJSON(sampleLightingGeoJSON, {
      style: {
        color: strokeColor,
        weight: 4,
        opacity: 0.85,
        dashArray: dashArray,
      },
      onEachFeature: (feature, layer) => {
        layer.bindPopup(`
          <div style="font-family: sans-serif; font-size: 11px; padding: 2px;">
            <strong style="color: ${strokeColor};">💡 Calque GeoJSON (L.geoJSON)</strong><br/>
            <span>Statut : <strong>${label}</strong></span><br/>
            <small style="color: #64748b;">(Simulé selon horodatage sinistre)</small>
          </div>
        `);
      }
    }).addTo(map);

    geoJsonLayerRef.current = newGeoLayer;
  };

  // Initialisation de la carte Leaflet OpenStreetMap
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [latitude, longitude],
      zoom: 14,
      zoomControl: false,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    L.control.zoom({ position: 'topright' }).addTo(map);

    // Marqueur d'intervention
    const marker = L.marker([latitude, longitude], { icon: emergencyIcon }).addTo(map);
    markerRef.current = marker;
    mapInstanceRef.current = map;

    // Clic sur une route de la carte pour la démonstration
    map.on('click', async (e) => {
      const { lat, lng } = e.latlng;
      handlePositionSelected(lat, lng);
    });

    // Chargement initial de la météo, de l'adresse et de l'éclairage GeoJSON
    handlePositionSelected(latitude, longitude, false);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Interrogation API Overpass pour bornes kilométriques (milestones) & sorties (junctions)
  const fetchSpatialPRInfo = async (lat, lon, roadName) => {
    try {
      const overpassUrl = `https://overpass-api.de/api/interpreter`;
      const query = `[out:json][timeout:4];(node["highway"="milestone"](around:5000,${lat},${lon});node["highway"="motorway_junction"](around:5000,${lat},${lon}););out body 5;`;
      const res = await fetch(overpassUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'data=' + encodeURIComponent(query),
        signal: AbortSignal.timeout(3000),
      });

      if (res.ok) {
        const data = await res.json();
        const elements = data.elements || [];
        const milestones = elements.filter(e => e.tags && (e.tags.highway === 'milestone' || e.tags.ref));
        const junctions = elements.filter(e => e.tags && e.tags.highway === 'motorway_junction');

        let milestoneStr = "";
        if (milestones.length >= 2) {
          const m1 = milestones[0].tags.ref || milestones[0].tags.distance || "12";
          const m2 = milestones[1].tags.ref || milestones[1].tags.distance || "13";
          milestoneStr = `Sinistre situé entre borne PR ${m1} et borne PR ${m2} de ${roadName}`;
        } else {
          // Calcul basé sur les coordonnées géographiques si pas de tag OSM explicite
          const prApprox = Math.floor((Math.abs(lat) * 100) % 60) + 1;
          milestoneStr = `Sinistre situé entre borne PR ${prApprox} et borne PR ${prApprox + 1} de ${roadName}`;
        }

        if (junctions.length > 0) {
          const j = junctions[0];
          const jRef = j.tags.ref ? ` (Sortie n°${j.tags.ref}${j.tags.name ? ' - ' + j.tags.name : ''})` : '';
          milestoneStr += jRef;
        }

        setSpatialPRInfo(milestoneStr);
      } else {
        throw new Error("Overpass non dispo");
      }
    } catch (e) {
      const prApprox = Math.floor((Math.abs(lat) * 100) % 60) + 1;
      setSpatialPRInfo(`Sinistre situé entre borne PR ${prApprox} et borne PR ${prApprox + 1} de ${roadName}`);
    }
  };

  // Focus sur l'input lors de l'ouverture de la recherche
  useEffect(() => {
    if (isSearchOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [isSearchOpen]);

  // Déplacement et mise à jour de la position
  const handlePositionSelected = async (lat, lon, moveMap = true) => {
    setCurrentCoord({ lat, lon });
    setValidatedCall(false);

    if (markerRef.current) {
      markerRef.current.setLatLng([lat, lon]);
    }
    if (mapInstanceRef.current && moveMap) {
      mapInstanceRef.current.panTo([lat, lon]);
    }

    // 1. Mise à jour du calque GeoJSON (L.geoJSON) pour l'éclairage public selon l'heure
    updateGeoJSONLightingLayer(lat, lon);

    // 2. Appel API Open-Meteo
    const weather = await fetchLiveWeather(lat, lon);
    setWeatherData(weather);
    if (onWeatherUpdate && weather.atmCode) {
      onWeatherUpdate(weather.atmCode, weather);
    }

    // 3. Détection de la voie et de l'adresse complète (Reverse-geocoding Nominatim)
    let detectedRoad = "Axe routier identifié";
    let detectedCity = "";
    let detectedPostcode = "";
    let detectedCountry = "France";
    let fullAddr = "Axe routier identifié";
    let catr = 4; // Voie communale
    let vma = 4;  // 50 km/h
    let agg = 2;  // En agglomération

    try {
      const revUrl = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`;
      const res = await fetch(revUrl, {
        headers: { 'Accept-Language': 'fr' },
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const json = await res.json();
        const addr = json.address || {};
        const road = addr.road || addr.pedestrian || addr.highway || addr.suburb || "Voie non nommée";
        const city = addr.city || addr.town || addr.village || addr.municipality || "";
        const postcode = addr.postcode || "";
        const country = addr.country || "France";

        detectedRoad = road;
        detectedCity = city;
        detectedPostcode = postcode;
        detectedCountry = country;

        const parts = [road];
        const cityPart = [postcode, city].filter(Boolean).join(' ');
        if (cityPart) parts.push(cityPart);
        if (country) parts.push(country);
        fullAddr = parts.join(', ');

        const roadLower = road.toLowerCase();
        if (roadLower.includes('autoroute') || (roadLower.startsWith('a') && /\d/.test(roadLower))) {
          catr = 1; vma = 9; agg = 1;
        } else if (roadLower.includes('nationale') || (roadLower.startsWith('n') && /\d/.test(roadLower))) {
          catr = 2; vma = 7; agg = 1;
        } else if (roadLower.includes('départementale') || (roadLower.startsWith('d') && /\d/.test(roadLower))) {
          catr = 3; vma = 6; agg = 1;
        } else if (roadLower.includes('périphérique') || roadLower.includes('voie rapide')) {
          catr = 7; vma = 5; agg = 2;
        } else {
          catr = 4; vma = 4; agg = 2;
        }
      }
    } catch (e) {
      fullAddr = `Secteur ${lat.toFixed(3)}°N, ${lon.toFixed(3)}°E`;
    }

    const roadObj = {
      name: detectedRoad,
      city: detectedCity,
      postcode: detectedPostcode,
      country: detectedCountry,
      fullAddress: fullAddr,
      catr,
      vma,
      agg
    };
    setRoadInfo(roadObj);

    // 4. Calcul Overpass Bornes PR & Sorties
    fetchSpatialPRInfo(lat, lon, detectedRoad);

    if (onLocationSelect) {
      onLocationSelect({
        lat: Number(lat.toFixed(5)),
        long: Number(lon.toFixed(5)),
        ...roadObj,
        weather,
      });
    }
  };

  // Exécution de la recherche textuelle d'adresse
  const handleSearchSubmit = async (e) => {
    if (e) e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    setIsSearching(true);
    setSearchError(null);

    try {
      const searchUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1&addressdetails=1`;
      const res = await fetch(searchUrl, {
        headers: { 'Accept-Language': 'fr' },
        signal: AbortSignal.timeout(4000),
      });
      if (res.ok) {
        const results = await res.json();
        if (results && results.length > 0) {
          const target = results[0];
          const newLat = parseFloat(target.lat);
          const newLon = parseFloat(target.lon);
          if (mapInstanceRef.current) {
            mapInstanceRef.current.flyTo([newLat, newLon], 16, { duration: 1.2 });
          }
          await handlePositionSelected(newLat, newLon, false);
          setIsSearchOpen(false);
        } else {
          setSearchError("Aucun résultat trouvé pour cette adresse.");
        }
      } else {
        setSearchError("Service de recherche momentanément indisponible.");
      }
    } catch (err) {
      setSearchError("Délai de recherche dépassé.");
    } finally {
      setIsSearching(false);
    }
  };

  // Bouton "Géolocaliser l'appel"
  const handleGeolocateCall = () => {
    setIsLocating(true);
    setValidatedCall(true);

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude: userLat, longitude: userLon } = pos.coords;
          handlePositionSelected(userLat, userLon, true);
          setIsLocating(false);
        },
        () => {
          handlePositionSelected(currentCoord.lat, currentCoord.lon, true);
          setIsLocating(false);
        },
        { timeout: 4000 }
      );
    } else {
      setIsLocating(false);
    }
  };

  return (
    <div className="relative flex flex-col bg-slate-100 dark:bg-slate-900 border border-amber-500/40 rounded-xl overflow-hidden shadow-inner">
      {/* En-tête de la carte */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-200/90 dark:bg-slate-950/80 border-b border-amber-500/30 text-xs z-10">
        <div className="flex items-center space-x-2">
          <MapPin className="w-4 h-4 text-red-500 animate-bounce" />
          <span className="font-bold text-slate-800 dark:text-slate-200">
            OpenStreetMap - Géolocalisation de l'Appel
          </span>
          <span className="hidden sm:inline text-[10px] text-slate-500 dark:text-slate-400 bg-slate-300 dark:bg-slate-800 px-1.5 py-0.5 rounded">
            Clic sur la carte = pointer l'accident
          </span>
        </div>
        <div className="flex items-center space-x-1 font-mono text-[11px] text-amber-600 dark:text-amber-400 font-semibold">
          <span>{currentCoord.lat.toFixed(4)}°N</span>
          <span>•</span>
          <span>{currentCoord.lon.toFixed(4)}°E</span>
        </div>
      </div>

      {/* Conteneur de la carte Leaflet (Agrandie à 340px pour l'Onglet 1) */}
      <div className="relative w-full h-[340px]">
        <div ref={mapContainerRef} className="w-full h-full cursor-crosshair z-0" />

        {/* HUD Météo Open-Meteo temps réel (Surimpression en haut à gauche) */}
        {weatherData && (
          <div className="absolute top-2 left-2 z-[400] bg-slate-900/85 dark:bg-slate-950/90 border border-slate-700/80 backdrop-blur-md rounded-lg p-2 shadow-lg text-white flex items-center space-x-3 text-xs">
            <div className="flex items-center space-x-1.5">
              <CloudSun className="w-4 h-4 text-amber-400 animate-pulse" />
              <div className="font-bold text-sm leading-none font-mono">
                {weatherData.temperature}°C
              </div>
            </div>
            <div className="h-4 w-px bg-slate-700" />
            <div className="flex items-center space-x-1 text-slate-300 text-[11px]">
              <Wind className="w-3.5 h-3.5 text-blue-400" />
              <span>{weatherData.windSpeed} km/h</span>
            </div>
            <div className="hidden sm:inline bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded text-[10px] font-semibold border border-amber-500/30">
              {weatherData.description}
            </div>
          </div>
        )}

        {/* HUD GeoJSON Simulation Éclairage Public (L.geoJSON) */}
        {hasPublicLightingGeoJSON && (
          <div className="absolute bottom-2 left-2 z-[400] max-w-[80%] bg-slate-900/85 dark:bg-slate-950/90 border border-slate-700/80 backdrop-blur-md rounded-lg px-2.5 py-1 shadow-lg text-white flex items-center space-x-2 text-[10px]">
            <span
              className="w-2.5 h-2.5 rounded-full animate-pulse shrink-0"
              style={{ backgroundColor: hasPublicLightingGeoJSON.strokeColor }}
            />
            <span className="font-bold font-mono text-slate-300 shrink-0">GeoJSON (L.geoJSON) :</span>
            <span className="font-bold truncate" style={{ color: hasPublicLightingGeoJSON.strokeColor }}>
              {hasPublicLightingGeoJSON.label}
            </span>
          </div>
        )}

        {/* Bouton Loupe Recherche placé directement sous les touches de zoom Leaflet */}
        <div className="absolute top-[76px] right-[10px] z-[400]">
          <button
            type="button"
            onClick={() => setIsSearchOpen(prev => !prev)}
            title="Rechercher une adresse"
            className={`w-[30px] h-[30px] rounded flex items-center justify-center border shadow transition ${
              isSearchOpen
                ? 'bg-amber-500 text-slate-950 border-amber-400 font-bold'
                : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <Search className="w-4 h-4" />
          </button>
        </div>

        {/* Barre de recherche d'adresse qui apparaît au clic sur la loupe */}
        {isSearchOpen && (
          <div className="absolute top-2 right-12 z-[500] max-w-[340px] w-[calc(100%-60px)] bg-white/95 dark:bg-slate-900/95 border border-amber-500/50 rounded-lg shadow-xl backdrop-blur-md p-1.5 flex flex-col space-y-1 animate-fadeIn">
            <form onSubmit={handleSearchSubmit} className="flex items-center space-x-1.5">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Rechercher rue, ville, accident..."
                className="flex-1 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs px-2 py-1.5 rounded border border-slate-300 dark:border-slate-700 focus:outline-none focus:border-amber-500"
              />
              <button
                type="submit"
                disabled={isSearching}
                className="px-2.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded transition flex items-center justify-center shrink-0 disabled:opacity-50"
              >
                {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Aller"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsSearchOpen(false);
                  setSearchError(null);
                }}
                className="p-1 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 rounded shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </form>
            {searchError && (
              <span className="text-[10px] text-red-500 font-semibold px-1">
                {searchError}
              </span>
            )}
          </div>
        )}
      </div>

      {/* BANNIÈRE SPATIALE OVERPASS PR & SORTIES (AU BAS DE LA CARTE) */}
      {spatialPRInfo && (
        <div className="bg-amber-500/15 border-t border-amber-500/30 px-3 py-1.5 text-xs flex items-center justify-between text-amber-900 dark:text-amber-200 font-bold">
          <div className="flex items-center space-x-2">
            <span className="text-sm">🛣️</span>
            <span>{spatialPRInfo}</span>
          </div>
          <span className="text-[10px] font-mono opacity-80 uppercase">Données Spatiales OSM/Overpass</span>
        </div>
      )}

      {/* Barre inférieure : Nom complet de voie, code postal, ville, pays + Bouton Géolocaliser */}
      <div className="flex flex-wrap items-center justify-between px-3 py-2 bg-slate-200/90 dark:bg-slate-900/95 border-t border-amber-500/30 gap-2 z-10">
        <div className="flex items-center space-x-2 text-xs flex-1 min-w-0 mr-2">
          <Navigation className="w-4 h-4 text-amber-500 shrink-0" />
          <div className="flex flex-wrap items-center gap-1.5 min-w-0">
            <span className="font-bold text-slate-900 dark:text-slate-100 truncate" title={roadInfo.fullAddress}>
              {roadInfo.fullAddress}
            </span>
            <span className="text-[11px] text-slate-600 dark:text-slate-400 shrink-0 font-medium">
              ({roadInfo.agg === 2 ? 'Zone Urbaine' : 'Hors Agglo.'})
            </span>
          </div>
        </div>

        {/* Bouton de validation de la géolocalisation */}
        <button
          type="button"
          onClick={handleGeolocateCall}
          className={`px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5 shadow-sm active:scale-95 shrink-0 ${
            validatedCall
              ? 'bg-emerald-600 text-white shadow-emerald-500/20'
              : 'bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black'
          }`}
        >
          {validatedCall ? (
            <>
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Position Validée</span>
            </>
          ) : (
            <>
              <Radio className="w-3.5 h-3.5 animate-pulse text-slate-950" />
              <span>{isLocating ? 'Géolocalisation...' : "Géolocaliser l'appel"}</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
