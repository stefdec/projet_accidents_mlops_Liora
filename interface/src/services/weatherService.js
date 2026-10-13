/**
 * Service d'intégration météo en temps réel via l'API Open-Meteo
 * Traduit automatiquement les codes WMO en modalités BAAC pour la variable 'atm'.
 */

export async function fetchLiveWeather(latitude, longitude) {
  try {
    const lat = Number(latitude) || 48.8566;
    const lon = Number(longitude) || 2.3522;

    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation&timezone=auto`;
    
    const response = await fetch(url, { signal: AbortSignal.timeout(3500) });
    if (!response.ok) {
      throw new Error(`Open-Meteo code: ${response.status}`);
    }

    const data = await response.json();
    const current = data.current || {};
    const code = current.weather_code || 0;
    const temp = Math.round(current.temperature_2m ?? 18);
    const wind = Math.round(current.wind_speed_10m ?? 10);
    const rain = current.precipitation ?? 0;

    // Correspondance WMO -> BAAC `atm`
    // 1: Normale, 2: Pluie légère, 3: Pluie forte, 4: Neige/grêle, 5: Brouillard, 6: Vent fort, 7: Éblouissant, 8: Couvert, 9: Autre
    let atmCode = 1;
    let description = "Ciel dégagé";

    if (wind > 50) {
      atmCode = 6; // Vent fort / Tempête
      description = `Vent violent (${wind} km/h)`;
    } else if (code === 0) {
      atmCode = 1; // Normale
      description = "Ensoleillé / Dégagé";
    } else if (code === 1 || code === 2) {
      atmCode = 1; // Légèrement voilé
      description = "Éclaircies";
    } else if (code === 3) {
      atmCode = 8; // Couvert
      description = "Ciel couvert";
    } else if (code === 45 || code === 48) {
      atmCode = 5; // Brouillard / Fumée
      description = "Brouillard épais";
    } else if (code >= 51 && code <= 57) {
      atmCode = 2; // Bruine / Pluie légère
      description = "Bruine / Pluie fine";
    } else if (code >= 61 && code <= 65) {
      atmCode = rain > 4 ? 3 : 2; // Pluie légère ou forte
      description = rain > 4 ? "Pluie battante" : "Pluie modérée";
    } else if (code >= 71 && code <= 77) {
      atmCode = 4; // Neige / Grêle
      description = "Chutes de neige";
    } else if (code >= 80 && code <= 82) {
      atmCode = 3; // Averses fortes
      description = "Averses fortes";
    } else if (code >= 85 && code <= 86) {
      atmCode = 4; // Averses de neige
      description = "Averses de neige";
    } else if (code >= 95) {
      atmCode = 6; // Orage / Vent fort
      description = "Orage violent";
    }

    return {
      success: true,
      temperature: temp,
      windSpeed: wind,
      precipitation: rain,
      weatherCode: code,
      atmCode,
      description,
    };
  } catch (err) {
    console.warn("Échec récupération météo live Open-Meteo:", err.message);
    return {
      success: false,
      temperature: 19,
      windSpeed: 12,
      precipitation: 0,
      weatherCode: 0,
      atmCode: 1,
      description: "Météo estimée (Normale)",
    };
  }
}
