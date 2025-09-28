import React, { useState, useEffect, useRef } from 'react';
import Map, { Marker, Source, Layer, MapRef } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Car, api } from '../services/api';

interface RealtimeMapViewProps {
  cars: Car[];
  selectedCarId?: number;
  onCarSelect: (carId: number) => void;
  geoJsonPolygon?: GeoJSON.Feature<GeoJSON.Polygon>;
  serviceStations?: Array<{
    id: string;
    position: [number, number];
    queueLength: number;
  }>;
  timeSpeed: number;
  onTimeSpeedChange: (speed: number) => void;
  onAddStation: (position: [number, number]) => void;
  simulationId?: string | null;
}

// You'll need to get a Mapbox access token
const MAPBOX_ACCESS_TOKEN = process.env.REACT_APP_MAPBOX_ACCESS_TOKEN || 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example';

const RealtimeMapView: React.FC<RealtimeMapViewProps> = ({
  cars,
  selectedCarId,
  onCarSelect,
  geoJsonPolygon,
  serviceStations = [],
  timeSpeed,
  onTimeSpeedChange,
  onAddStation,
  simulationId
}) => {
  const mapRef = useRef<MapRef>(null);
  const [viewState, setViewState] = useState({
    longitude: -106.4850,
    latitude: 31.7619,
    zoom: 13
  });

  // Convert car positions to coordinates (mock for now)
  const getCarCoordinates = (car: Car): [number, number] => {
    // Mock coordinates around El Paso
    const baseLat = 31.7619;
    const baseLng = -106.4850;

    // Spread based on car position in queue
    const offset = car.position * 0.0001; // Small offset per meter
    return [baseLng + offset, baseLat + offset];
  };

  const handleMapClick = (event: any) => {
    const { lng, lat } = event.lngLat;
    onAddStation([lng, lat]);
  };

  const handleTimeSpeedChange = async (speed: number) => {
    if (simulationId) {
      try {
        await api.updateTimeSpeed(simulationId, speed);
        onTimeSpeedChange(speed);
      } catch (error) {
        console.error('Failed to update time speed:', error);
      }
    }
  };

  return (
    <div style={{ height: '600px', position: 'relative' }}>
      {/* Time Controls */}
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        zIndex: 1,
        background: 'white',
        padding: '10px',
        borderRadius: '4px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <label>Time Speed: </label>
        <select
          value={timeSpeed}
          onChange={(e) => handleTimeSpeedChange(Number(e.target.value))}
        >
          <option value={0.5}>0.5x</option>
          <option value={1}>1x</option>
          <option value={2}>2x</option>
          <option value={4}>4x</option>
        </select>
      </div>

      <Map
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/streets-v12"
        mapboxAccessToken={MAPBOX_ACCESS_TOKEN}
        onClick={handleMapClick}
        ref={mapRef}
      >
        {/* GeoJSON Polygon Layer */}
        {geoJsonPolygon && (
          <Source id="border-polygon" type="geojson" data={geoJsonPolygon}>
            <Layer
              id="border-fill"
              type="fill"
              paint={{
                'fill-color': '#0080ff',
                'fill-opacity': 0.2
              }}
            />
            <Layer
              id="border-line"
              type="line"
              paint={{
                'line-color': '#0080ff',
                'line-width': 2
              }}
            />
          </Source>
        )}

        {/* Car Markers */}
        {cars.map(car => {
          const [lng, lat] = getCarCoordinates(car);
          const isSelected = car.car_id === selectedCarId;

          return (
            <Marker
              key={car.car_id}
              longitude={lng}
              latitude={lat}
              onClick={() => onCarSelect(car.car_id)}
            >
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  backgroundColor: isSelected ? 'red' : 'blue',
                  borderRadius: '50%',
                  border: '2px solid white',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '10px',
                  color: 'white',
                  fontWeight: 'bold'
                }}
                title={`Car ${car.car_id}: ${car.velocity.toFixed(1)} m/s`}
              >
                {car.car_id}
              </div>
            </Marker>
          );
        })}

        {/* Service Station Markers */}
        {serviceStations.map(station => (
          <Marker
            key={station.id}
            longitude={station.position[0]}
            latitude={station.position[1]}
          >
            <div
              style={{
                width: '30px',
                height: '30px',
                backgroundColor: 'green',
                borderRadius: '4px',
                border: '2px solid white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                color: 'white',
                fontWeight: 'bold'
              }}
              title={`Station ${station.id}: ${station.queueLength} cars`}
            >
              {station.queueLength}
            </div>
          </Marker>
        ))}
      </Map>
    </div>
  );
};

export default RealtimeMapView;