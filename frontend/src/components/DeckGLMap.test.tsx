import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-map-gl
jest.mock('react-map-gl', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-map">{children}</div>
  ),
  NavigationControl: () => <div data-testid="mock-nav-control" />,
  useMap: () => ({ current: null }),
}));

// Import after mocks are set up
import DeckGLMap, { CarData, ServiceNodeData } from './DeckGLMap';
import { getCarColor, CAR_COLORS } from './layers/CarLayer';

describe('DeckGLMap', () => {
  const mockCars: CarData[] = [
    {
      id: 'car-1',
      position: [-106.4867, 31.7508],
      status: 'approaching',
      velocity: 10.5,
      acceleration: 0.5,
    },
    {
      id: 'car-2',
      position: [-106.4870, 31.7510],
      status: 'queued',
      velocity: 0,
      acceleration: 0,
      queue_id: 1,
      queue_position: 2,
    },
    {
      id: 'car-3',
      position: [-106.4872, 31.7512],
      status: 'serving',
      velocity: 0,
      acceleration: 0,
      queue_id: 1,
    },
  ];

  const mockServiceNodes: ServiceNodeData[] = [
    {
      node_id: 'node-1',
      queue_id: 1,
      is_busy: true,
      current_car_id: 3,
      service_rate: 0.25,
      total_served: 10,
      position: [-106.4875, 31.7515],
    },
  ];

  const defaultProps = {
    cars: mockCars,
    serviceNodes: mockServiceNodes,
    mapCenter: [-106.4867, 31.7508] as [number, number],
    zoom: 15,
    onCarClick: jest.fn(),
    selectedCarId: null,
    showPaths: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the map container', () => {
      render(<DeckGLMap {...defaultProps} />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });

    it('renders the mock map', () => {
      render(<DeckGLMap {...defaultProps} />);
      expect(screen.getByTestId('mock-map')).toBeInTheDocument();
    });

    it('renders with no cars', () => {
      render(<DeckGLMap {...defaultProps} cars={[]} />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });

    it('renders with no service nodes', () => {
      render(<DeckGLMap {...defaultProps} serviceNodes={[]} />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });
  });

  describe('Props Handling', () => {
    it('updates when cars prop changes', () => {
      const { rerender } = render(<DeckGLMap {...defaultProps} />);

      const newCars = [
        ...mockCars,
        {
          id: 'car-4',
          position: [-106.4880, 31.7520] as [number, number],
          status: 'approaching' as const,
          velocity: 12,
          acceleration: 0.3,
        },
      ];

      rerender(<DeckGLMap {...defaultProps} cars={newCars} />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });

    it('respects showPaths prop', () => {
      const { rerender } = render(<DeckGLMap {...defaultProps} showPaths={true} />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();

      rerender(<DeckGLMap {...defaultProps} showPaths={false} />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });

    it('updates map center correctly', () => {
      const newCenter: [number, number] = [-106.5000, 31.8000];
      render(<DeckGLMap {...defaultProps} mapCenter={newCenter} />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });

    it('handles selected car id', () => {
      render(<DeckGLMap {...defaultProps} selectedCarId="car-1" />);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('handles large number of cars efficiently', () => {
      const largeCarsArray: CarData[] = Array.from({ length: 5000 }, (_, i) => ({
        id: `car-${i}`,
        position: [-106.4867 + (i * 0.0001), 31.7508 + (i * 0.0001)] as [number, number],
        status: ['approaching', 'queued', 'serving'][i % 3] as 'approaching' | 'queued' | 'serving',
        velocity: Math.random() * 10,
        acceleration: Math.random() * 2,
      }));

      const startTime = performance.now();
      render(<DeckGLMap {...defaultProps} cars={largeCarsArray} />);
      const endTime = performance.now();

      // Initial render should complete in under 500ms (generous for test environment)
      expect(endTime - startTime).toBeLessThan(500);
      expect(screen.getByTestId('deckgl-map-container')).toBeInTheDocument();
    });
  });
});

describe('CarLayer utilities', () => {
  describe('getCarColor', () => {
    it('returns correct color for approaching status', () => {
      expect(getCarColor('approaching')).toEqual([0, 123, 255, 200]);
    });

    it('returns correct color for arriving status', () => {
      expect(getCarColor('arriving')).toEqual([0, 123, 255, 200]);
    });

    it('returns correct color for queued status', () => {
      expect(getCarColor('queued')).toEqual([255, 193, 7, 200]);
    });

    it('returns correct color for serving status', () => {
      expect(getCarColor('serving')).toEqual([40, 167, 69, 200]);
    });

    it('returns correct color for completed status', () => {
      expect(getCarColor('completed')).toEqual([220, 53, 69, 200]);
    });

    it('returns default color for unknown status', () => {
      expect(getCarColor('unknown')).toEqual([108, 117, 125, 200]);
    });
  });

  describe('CAR_COLORS constant', () => {
    it('has all required status colors', () => {
      expect(CAR_COLORS).toHaveProperty('approaching');
      expect(CAR_COLORS).toHaveProperty('arriving');
      expect(CAR_COLORS).toHaveProperty('queued');
      expect(CAR_COLORS).toHaveProperty('serving');
      expect(CAR_COLORS).toHaveProperty('completed');
      expect(CAR_COLORS).toHaveProperty('default');
    });

    it('colors are in RGBA format', () => {
      Object.values(CAR_COLORS).forEach((color) => {
        expect(color).toHaveLength(4);
        color.forEach((value) => {
          expect(value).toBeGreaterThanOrEqual(0);
          expect(value).toBeLessThanOrEqual(255);
        });
      });
    });
  });
});

describe('CarLayer creation', () => {
  it('exports createCarLayer function', async () => {
    const { createCarLayer } = await import('./layers/CarLayer');
    expect(createCarLayer).toBeDefined();
    expect(typeof createCarLayer).toBe('function');
  });

  it('creates a layer with correct id', async () => {
    const { createCarLayer } = await import('./layers/CarLayer');
    const layer = createCarLayer({
      cars: [],
      selectedCarId: null,
    });
    expect(layer.id).toBe('car-layer');
  });

  it('creates a layer with car data', async () => {
    const { createCarLayer } = await import('./layers/CarLayer');
    const testCars: CarData[] = [
      { id: 'car-1', position: [-106.4867, 31.7508], status: 'approaching' },
    ];
    const layer = createCarLayer({
      cars: testCars,
      selectedCarId: null,
    });
    expect(layer.props.data).toEqual(testCars);
  });
});

describe('PathLayer creation', () => {
  it('exports createPathLayer function', async () => {
    const { createPathLayer } = await import('./layers/PathLayer');
    expect(createPathLayer).toBeDefined();
    expect(typeof createPathLayer).toBe('function');
  });

  it('returns null when showPaths is false', async () => {
    const { createPathLayer } = await import('./layers/PathLayer');
    const layer = createPathLayer({
      cars: [],
      selectedCarId: null,
      showPaths: false,
    });
    expect(layer).toBeNull();
  });

  it('returns null when no cars have paths', async () => {
    const { createPathLayer } = await import('./layers/PathLayer');
    const carsWithoutPaths: CarData[] = [
      { id: 'car-1', position: [-106.4867, 31.7508], status: 'approaching' },
    ];
    const layer = createPathLayer({
      cars: carsWithoutPaths,
      selectedCarId: null,
      showPaths: true,
    });
    expect(layer).toBeNull();
  });

  it('creates a layer when cars have paths', async () => {
    const { createPathLayer } = await import('./layers/PathLayer');
    const carsWithPaths: CarData[] = [
      {
        id: 'car-1',
        position: [-106.4867, 31.7508],
        status: 'approaching',
        path: {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: [[-106.4867, 31.7508], [-106.4870, 31.7510]],
          },
          properties: {},
        },
      },
    ];
    const layer = createPathLayer({
      cars: carsWithPaths,
      selectedCarId: null,
      showPaths: true,
    });
    expect(layer).not.toBeNull();
    expect(layer?.id).toBe('car-paths-layer');
  });
});
