import { ScatterplotLayer } from '@deck.gl/layers';
import type { PickingInfo } from '@deck.gl/core';

export interface CarData {
  id: string;
  position: [number, number]; // [longitude, latitude]
  status: 'approaching' | 'arriving' | 'queued' | 'serving' | 'completed';
  velocity?: number;
  acceleration?: number;
  queue_id?: number;
  queue_position?: number;
  path?: any; // GeoJSON Feature
  status_start_time?: number;
}

// Color palette for car status (RGBA)
export const CAR_COLORS: Record<string, [number, number, number, number]> = {
  approaching: [0, 123, 255, 200],    // Blue
  arriving: [0, 123, 255, 200],       // Blue (same as approaching)
  queued: [255, 193, 7, 200],         // Yellow
  serving: [40, 167, 69, 200],        // Green
  completed: [220, 53, 69, 200],      // Red
  default: [108, 117, 125, 200],      // Gray
};

// Selected car colors (more opaque/bright)
export const SELECTED_CAR_COLORS: Record<string, [number, number, number, number]> = {
  approaching: [0, 123, 255, 255],
  arriving: [0, 123, 255, 255],
  queued: [255, 193, 7, 255],
  serving: [40, 167, 69, 255],
  completed: [220, 53, 69, 255],
  default: [108, 117, 125, 255],
};

export function getCarColor(status: string): [number, number, number, number] {
  return CAR_COLORS[status] || CAR_COLORS.default;
}

export function getSelectedCarColor(status: string): [number, number, number, number] {
  return SELECTED_CAR_COLORS[status] || SELECTED_CAR_COLORS.default;
}

export interface CarLayerProps {
  cars: CarData[];
  selectedCarId: string | null;
  onCarClick?: (car: CarData) => void;
  onCarHover?: (car: CarData | null) => void;
  updateTrigger?: number; // Trigger re-render when this changes
}

/**
 * Creates a deck.gl ScatterplotLayer for rendering cars
 * Uses GPU instanced rendering for efficient handling of thousands of cars
 */
export function createCarLayer({
  cars,
  selectedCarId,
  onCarClick,
  onCarHover,
  updateTrigger = 0,
}: CarLayerProps): ScatterplotLayer<CarData> {
  return new ScatterplotLayer<CarData>({
    id: 'car-layer',
    data: cars,

    // Position accessor - extract [lon, lat] from car data
    getPosition: (d: CarData) => d.position,

    // Radius based on selection state
    getRadius: (d: CarData) => (d.id === selectedCarId ? 12 : 8),

    // Color based on status and selection
    getFillColor: (d: CarData) =>
      d.id === selectedCarId
        ? getSelectedCarColor(d.status)
        : getCarColor(d.status),

    // Line/stroke for selected car
    getLineColor: (d: CarData) =>
      d.id === selectedCarId
        ? [255, 255, 255, 255]
        : [255, 255, 255, 200],
    getLineWidth: (d: CarData) => (d.id === selectedCarId ? 3 : 2),
    stroked: true,

    // Enable picking for click/hover interactions
    pickable: true,

    // Auto-highlight on hover
    autoHighlight: true,
    highlightColor: [255, 255, 255, 100],

    // Sizing in pixels (not meters)
    radiusUnits: 'pixels',
    lineWidthUnits: 'pixels',

    // Minimum and maximum radius for zoom levels
    radiusMinPixels: 4,
    radiusMaxPixels: 20,

    // Click handler
    onClick: (info: PickingInfo<CarData>) => {
      if (info.object && onCarClick) {
        onCarClick(info.object);
      }
    },

    // Hover handler
    onHover: (info: PickingInfo<CarData>) => {
      if (onCarHover) {
        onCarHover(info.object || null);
      }
    },

    // Update triggers for efficient re-rendering
    // Only re-render when these values change
    updateTriggers: {
      getPosition: updateTrigger,
      getFillColor: [updateTrigger, selectedCarId],
      getRadius: selectedCarId,
      getLineWidth: selectedCarId,
    },

    // Transition for smooth animations
    transitions: {
      getPosition: {
        duration: 100, // 100ms transition for smooth movement
        easing: (t: number) => t, // Linear easing
      },
    },

    // Performance optimizations
    // ScatterplotLayer has built-in optimizations
  });
}

export default createCarLayer;
