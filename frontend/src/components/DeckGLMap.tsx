import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Map, { NavigationControl, useMap } from 'react-map-gl';
import { MapboxOverlay } from '@deck.gl/mapbox';
import type { Layer } from '@deck.gl/core';
import { ScatterplotLayer, IconLayer } from '@deck.gl/layers';
import 'mapbox-gl/dist/mapbox-gl.css';

import { createCarLayer, CarData, getCarColor } from './layers/CarLayer';
import { createPathLayer } from './layers/PathLayer';

// Re-export types and utilities for external use
export type { CarData } from './layers/CarLayer';
export { getCarColor } from './layers/CarLayer';

export interface ServiceNodeData {
  node_id: string;
  queue_id: number;
  is_busy: boolean;
  current_car_id?: number;
  service_rate: number;
  total_served: number;
  total_service_time?: number;
  position: [number, number]; // [longitude, latitude]
}

export interface SlowdownZone {
  type: 'booth' | 'slowdown';
  name: string;
  description: string;
  coordinates: [number, number];
  target_speed_mps?: number;
}

export interface DeckGLMapProps {
  cars: CarData[];
  serviceNodes?: ServiceNodeData[];
  slowdownZones?: SlowdownZone[];
  mapCenter: [number, number];
  zoom?: number;
  onCarClick?: (car: CarData) => void;
  onCarHover?: (car: CarData | null) => void;
  selectedCarId: string | null;
  showPaths?: boolean;
  mapStyle?: string;
}

// Booth/Zone icon colors
const BOOTH_COLOR: [number, number, number, number] = [231, 76, 60, 255]; // Red
const SLOWDOWN_COLOR: [number, number, number, number] = [243, 156, 18, 255]; // Orange

/**
 * DeckGLMapOverlay component that integrates deck.gl layers with MapLibre/Mapbox
 * Uses MapboxOverlay for seamless integration with react-map-gl
 */
function DeckGLMapOverlay({
  cars,
  serviceNodes,
  slowdownZones,
  selectedCarId,
  showPaths,
  onCarClick,
  onCarHover,
}: Omit<DeckGLMapProps, 'mapCenter' | 'zoom' | 'mapStyle'>) {
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const { current: mapRef } = useMap();
  const [updateCounter, setUpdateCounter] = useState(0);

  // Update counter when cars change for smooth transitions
  useEffect(() => {
    setUpdateCounter((c) => c + 1);
  }, [cars]);

  // Create the MapboxOverlay instance
  useEffect(() => {
    if (!mapRef) return;

    overlayRef.current = new MapboxOverlay({
      interleaved: true,
    });

    const map = mapRef.getMap();
    map.addControl(overlayRef.current as any);

    return () => {
      if (overlayRef.current && map) {
        map.removeControl(overlayRef.current as any);
      }
    };
  }, [mapRef]);

  // Build layers array
  const layers = useMemo(() => {
    const layersArray: Layer[] = [];

    // 1. Path layer (rendered first, behind cars)
    const pathLayer = createPathLayer({
      cars,
      selectedCarId,
      showPaths: showPaths ?? true,
      updateTrigger: updateCounter,
    });
    if (pathLayer) {
      layersArray.push(pathLayer);
    }

    // 2. Car layer (ScatterplotLayer)
    const carLayer = createCarLayer({
      cars,
      selectedCarId,
      onCarClick,
      onCarHover,
      updateTrigger: updateCounter,
    });
    layersArray.push(carLayer);

    // 3. Service nodes layer (if provided with positions)
    if (serviceNodes && serviceNodes.length > 0) {
      const nodesWithPosition = serviceNodes.filter((n) => n.position);
      if (nodesWithPosition.length > 0) {
        const serviceNodeLayer = new ScatterplotLayer<ServiceNodeData>({
          id: 'service-nodes-layer',
          data: nodesWithPosition,
          getPosition: (d) => d.position,
          getRadius: 14,
          getFillColor: (d) =>
            d.is_busy
              ? [40, 167, 69, 255] // Green when busy
              : [108, 117, 125, 255], // Gray when idle
          getLineColor: [255, 255, 255, 255],
          getLineWidth: 3,
          stroked: true,
          radiusUnits: 'pixels',
          lineWidthUnits: 'pixels',
          pickable: true,
          autoHighlight: true,
        });
        layersArray.push(serviceNodeLayer);
      }
    }

    // 4. Slowdown zones layer (if provided)
    if (slowdownZones && slowdownZones.length > 0) {
      const zoneLayer = new ScatterplotLayer<SlowdownZone>({
        id: 'slowdown-zones-layer',
        data: slowdownZones,
        getPosition: (d) => d.coordinates,
        getRadius: (d) => (d.type === 'booth' ? 14 : 12),
        getFillColor: (d) => (d.type === 'booth' ? BOOTH_COLOR : SLOWDOWN_COLOR),
        getLineColor: [255, 255, 255, 255],
        getLineWidth: 3,
        stroked: true,
        radiusUnits: 'pixels',
        lineWidthUnits: 'pixels',
        pickable: false,
      });
      layersArray.push(zoneLayer);
    }

    return layersArray;
  }, [cars, selectedCarId, showPaths, serviceNodes, slowdownZones, onCarClick, onCarHover, updateCounter]);

  // Update the overlay with new layers
  useEffect(() => {
    if (overlayRef.current) {
      overlayRef.current.setProps({ layers });
    }
  }, [layers]);

  return null;
}

/**
 * DeckGLMap - High-performance WebGL-based map for rendering thousands of cars
 *
 * Features:
 * - GPU instanced rendering via deck.gl ScatterplotLayer
 * - Handles 5000+ cars at 60 FPS
 * - Smooth position transitions
 * - Click/hover interactions
 * - Path visualization with GeoJsonLayer
 * - Service node and slowdown zone markers
 */
const DeckGLMap: React.FC<DeckGLMapProps> = ({
  cars,
  serviceNodes = [],
  slowdownZones = [],
  mapCenter,
  zoom = 15,
  onCarClick,
  onCarHover,
  selectedCarId,
  showPaths = true,
  mapStyle = 'mapbox://styles/gavargas/ck1yptdx72uqd1cn0x144h6sx',
}) => {
  // Check for Mapbox token
  const mapboxToken = process.env.REACT_APP_MAPBOX_TOKEN;

  if (!mapboxToken) {
    return (
      <div
        data-testid="deckgl-map-container"
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f0f0f0',
        }}
      >
        <div style={{ padding: '20px', backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '4px' }}>
          <p><strong>Warning:</strong> MapBox token not configured!</p>
          <p>Please add REACT_APP_MAPBOX_TOKEN to your .env file to display the map.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="deckgl-map-container"
      style={{ width: '100%', height: '100%', position: 'relative' }}
    >
      <Map
        initialViewState={{
          longitude: mapCenter[0],
          latitude: mapCenter[1],
          zoom,
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle={mapStyle}
        mapboxAccessToken={mapboxToken}
        // Disable default map interactions that conflict with deck.gl picking
        dragRotate={false}
        touchZoomRotate={false}
      >
        <DeckGLMapOverlay
          cars={cars}
          serviceNodes={serviceNodes}
          slowdownZones={slowdownZones}
          selectedCarId={selectedCarId}
          showPaths={showPaths}
          onCarClick={onCarClick}
          onCarHover={onCarHover}
        />
        <NavigationControl position="top-right" />
      </Map>
    </div>
  );
};

export default DeckGLMap;
