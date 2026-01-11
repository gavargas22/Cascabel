import { PathLayer as DeckPathLayer } from '@deck.gl/layers';
import { GeoJsonLayer } from '@deck.gl/layers';
import type { CarData } from './CarLayer';
import { CAR_COLORS, SELECTED_CAR_COLORS } from './CarLayer';

export interface PathLayerProps {
  cars: CarData[];
  selectedCarId: string | null;
  showPaths: boolean;
  updateTrigger?: number;
}

// Convert hex color to RGBA array
function hexToRgba(hex: string, alpha: number = 200): [number, number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (result) {
    return [
      parseInt(result[1], 16),
      parseInt(result[2], 16),
      parseInt(result[3], 16),
      alpha,
    ];
  }
  return [128, 128, 128, alpha]; // Default gray
}

// Default path color (gray, semi-transparent)
const DEFAULT_PATH_COLOR: [number, number, number, number] = [136, 136, 136, 40];
const SELECTED_PATH_COLOR: [number, number, number, number] = [136, 136, 136, 200];

/**
 * Creates a deck.gl GeoJsonLayer for rendering car paths
 * Each car has a unique GeoJSON path that it follows
 */
export function createPathLayer({
  cars,
  selectedCarId,
  showPaths,
  updateTrigger = 0,
}: PathLayerProps): GeoJsonLayer | null {
  if (!showPaths) {
    return null;
  }

  // Extract paths from cars that have them
  const pathData = cars
    .filter((car) => car.path && car.path.geometry)
    .map((car) => ({
      ...car.path,
      properties: {
        ...car.path.properties,
        carId: car.id,
        carStatus: car.status,
        isSelected: car.id === selectedCarId,
      },
    }));

  if (pathData.length === 0) {
    return null;
  }

  return new GeoJsonLayer({
    id: 'car-paths-layer',
    data: {
      type: 'FeatureCollection',
      features: pathData,
    },

    // Only render lines (not fills)
    filled: false,
    stroked: true,

    // Line styling
    getLineColor: (feature: any) => {
      const isSelected = feature.properties?.isSelected;
      const carStatus = feature.properties?.carStatus;

      if (isSelected) {
        // Use the car's status color for selected path
        return SELECTED_CAR_COLORS[carStatus] || SELECTED_PATH_COLOR;
      }
      // Dim path for non-selected cars
      return DEFAULT_PATH_COLOR;
    },

    getLineWidth: (feature: any) => {
      return feature.properties?.isSelected ? 3 : 1.5;
    },

    lineWidthUnits: 'pixels',
    lineWidthMinPixels: 1,
    lineWidthMaxPixels: 5,

    // Update triggers
    updateTriggers: {
      getLineColor: [selectedCarId, updateTrigger],
      getLineWidth: selectedCarId,
    },

    // Not pickable - paths are just for visualization
    pickable: false,
  });
}

/**
 * Creates a deck.gl PathLayer for a single car's path
 * Alternative to GeoJsonLayer when you have coordinate arrays directly
 */
export function createSinglePathLayer(
  pathId: string,
  coordinates: [number, number][],
  isSelected: boolean,
  color?: [number, number, number, number]
): DeckPathLayer {
  return new DeckPathLayer({
    id: `path-${pathId}`,
    data: [{ path: coordinates }],

    getPath: (d: { path: [number, number][] }) => d.path,
    getColor: color || (isSelected ? SELECTED_PATH_COLOR : DEFAULT_PATH_COLOR),
    getWidth: isSelected ? 3 : 1.5,

    widthUnits: 'pixels',
    widthMinPixels: 1,
    widthMaxPixels: 5,

    pickable: false,
  });
}

export default createPathLayer;
