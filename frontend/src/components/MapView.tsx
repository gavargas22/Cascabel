import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import { Icon, LatLngTuple } from 'leaflet';
import { Car } from '../services/api';
import 'leaflet/dist/leaflet.css';
import './MapView.css';

// Fix for default markers in react-leaflet
delete (Icon.Default.prototype as any)._getIconUrl;
Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

interface MapViewProps {
  cars: Car[];
  selectedCarId?: number;
  onCarSelect: (carId: number) => void;
  center?: LatLngTuple;
  zoom?: number;
}

const MapView: React.FC<MapViewProps> = ({
  cars,
  selectedCarId,
  onCarSelect,
  center = [31.7619, -106.4850], // Default to El Paso area
  zoom = 13
}) => {
  // Convert car positions to GPS coordinates
  // For now, we'll create mock coordinates around the center
  // In a real implementation, this would use actual GPS data from the simulation
  const getCarCoordinates = (car: Car): LatLngTuple => {
    // Create a spread around the center based on car position
    const baseLat = center[0];
    const baseLng = center[1];

    // Spread cars in a grid pattern based on their position
    const gridSize = Math.ceil(Math.sqrt(cars.length));
    const carIndex = cars.findIndex(c => c.car_id === car.car_id);

    const row = Math.floor(carIndex / gridSize);
    const col = carIndex % gridSize;

    // Spread over ~2km area
    const latOffset = (row - gridSize / 2) * 0.01; // ~1km lat
    const lngOffset = (col - gridSize / 2) * 0.015; // ~1km lng

    return [baseLat + latOffset, baseLng + lngOffset];
  };

  const getCarColor = (car: Car) => {
    switch (car.status) {
      case 'arriving': return '#4CAF50'; // Green
      case 'queued': return '#FF9800';   // Orange
      case 'serving': return '#2196F3';  // Blue
      case 'completed': return '#9C27B0'; // Purple
      default: return '#757575';         // Grey
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'arriving': return 'Arriving';
      case 'queued': return 'Queued';
      case 'serving': return 'Being Served';
      case 'completed': return 'Completed';
      default: return 'Unknown';
    }
  };

  return (
    <div className="map-view">
      <h2>Live Map View</h2>
      <div className="map-container">
        <MapContainer
          center={center}
          zoom={zoom}
          style={{ height: '500px', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {cars.map(car => {
            const coordinates = getCarCoordinates(car);
            const isSelected = selectedCarId === car.car_id;

            return (
              <div key={car.car_id}>
                {/* Car marker */}
                <Circle
                  center={coordinates}
                  radius={isSelected ? 15 : 10}
                  pathOptions={{
                    color: getCarColor(car),
                    fillColor: getCarColor(car),
                    fillOpacity: 0.8,
                    weight: isSelected ? 3 : 2
                  }}
                  eventHandlers={{
                    click: () => onCarSelect(car.car_id)
                  }}
                />

                {/* Popup with car details */}
                <Marker
                  position={coordinates}
                  eventHandlers={{
                    click: () => onCarSelect(car.car_id)
                  }}
                >
                  <Popup>
                    <div className="car-popup">
                      <h4>Car {car.car_id}</h4>
                      <p><strong>Status:</strong> {getStatusText(car.status)}</p>
                      <p><strong>Position:</strong> {car.position.toFixed(1)}m</p>
                      <p><strong>Velocity:</strong> {car.velocity.toFixed(1)} m/s</p>
                      {car.queue_id !== undefined && (
                        <p><strong>Queue:</strong> {car.queue_id + 1}</p>
                      )}
                      <p><strong>Coordinates:</strong><br />
                        {coordinates[0].toFixed(6)}, {coordinates[1].toFixed(6)}
                      </p>
                    </div>
                  </Popup>
                </Marker>
              </div>
            );
          })}
        </MapContainer>
      </div>

      <div className="map-legend">
        <h4>Legend</h4>
        <div className="legend-items">
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#4CAF50' }}></div>
            <span>Arriving</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#FF9800' }}></div>
            <span>Queued</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#2196F3' }}></div>
            <span>Being Served</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#9C27B0' }}></div>
            <span>Completed</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapView;