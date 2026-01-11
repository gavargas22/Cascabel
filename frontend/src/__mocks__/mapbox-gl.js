// Mock for mapbox-gl
const mapboxgl = {
  Map: jest.fn(() => ({
    on: jest.fn(),
    remove: jest.fn(),
    getCanvas: jest.fn(() => ({
      style: {},
    })),
    getContainer: jest.fn(() => document.createElement('div')),
    addControl: jest.fn(),
    removeControl: jest.fn(),
    hasControl: jest.fn(() => false),
    resize: jest.fn(),
    getBounds: jest.fn(() => ({
      toArray: () => [[-180, -90], [180, 90]],
    })),
    getCenter: jest.fn(() => ({ lng: 0, lat: 0 })),
    getZoom: jest.fn(() => 10),
    setCenter: jest.fn(),
    setZoom: jest.fn(),
    flyTo: jest.fn(),
    easeTo: jest.fn(),
    jumpTo: jest.fn(),
    project: jest.fn(() => ({ x: 0, y: 0 })),
    unproject: jest.fn(() => ({ lng: 0, lat: 0 })),
    queryRenderedFeatures: jest.fn(() => []),
    addSource: jest.fn(),
    removeSource: jest.fn(),
    getSource: jest.fn(),
    addLayer: jest.fn(),
    removeLayer: jest.fn(),
    getLayer: jest.fn(),
    setPaintProperty: jest.fn(),
    setLayoutProperty: jest.fn(),
    loaded: jest.fn(() => true),
  })),
  NavigationControl: jest.fn(() => ({
    onAdd: jest.fn(),
    onRemove: jest.fn(),
  })),
  Marker: jest.fn(() => ({
    setLngLat: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn(),
    getElement: jest.fn(() => document.createElement('div')),
  })),
  Popup: jest.fn(() => ({
    setLngLat: jest.fn().mockReturnThis(),
    setHTML: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn(),
  })),
  LngLatBounds: jest.fn(() => ({
    extend: jest.fn().mockReturnThis(),
    toArray: jest.fn(() => [[-180, -90], [180, 90]]),
  })),
  supported: jest.fn(() => true),
};

module.exports = mapboxgl;
module.exports.default = mapboxgl;
