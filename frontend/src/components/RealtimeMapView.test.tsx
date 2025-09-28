import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import RealtimeMapView from './RealtimeMapView';
import { Car } from '../services/api';

// Mock mapbox-gl to avoid DOM issues in tests
jest.mock('react-map-gl', () => {
  const MockMap = ({ children, ...props }: any) => (
    <div data-testid="mapbox-map" {...props}>
      {children}
    </div>
  );
  const MockMarker = ({ children, ...props }: any) => (
    <div data-testid="mapbox-marker" {...props}>
      {children}
    </div>
  );
  const MockSource = ({ children }: any) => <div data-testid="mapbox-source">{children}</div>;
  const MockLayer = (props: any) => <div data-testid="mapbox-layer" {...props} />;

  return {
    Map: MockMap,
    Marker: MockMarker,
    Source: MockSource,
    Layer: MockLayer,
    default: MockMap
  };
});

// Mock mapbox-gl CSS
jest.mock('mapbox-gl/dist/mapbox-gl.css', () => ({}));

const mockCars: Car[] = [
  {
    car_id: 1,
    position: 10.0,
    velocity: 5.0,
    status: 'queued',
    queue_id: 1
  },
  {
    car_id: 2,
    position: 8.0,
    velocity: 3.0,
    status: 'queued',
    queue_id: 1
  }
];

const mockGeoJsonPolygon: GeoJSON.Feature<GeoJSON.Polygon> = {
  type: 'Feature',
  geometry: {
    type: 'Polygon',
    coordinates: [[
      [-106.5, 31.7],
      [-106.4, 31.7],
      [-106.4, 31.8],
      [-106.5, 31.8],
      [-106.5, 31.7]
    ]]
  },
  properties: {}
};

const mockServiceStations = [
  {
    id: 'station-1',
    position: [-106.4850, 31.7619] as [number, number],
    queueLength: 3
  }
];

describe('RealtimeMapView', () => {
  const defaultProps = {
    cars: mockCars,
    selectedCarId: undefined,
    onCarSelect: jest.fn(),
    geoJsonPolygon: mockGeoJsonPolygon,
    serviceStations: mockServiceStations,
    timeSpeed: 1,
    onTimeSpeedChange: jest.fn(),
    onAddStation: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders map container', () => {
    render(<RealtimeMapView {...defaultProps} />);
    expect(screen.getByTestId('mapbox-map')).toBeInTheDocument();
  });

  it('renders car markers', () => {
    render(<RealtimeMapView {...defaultProps} />);
    const markers = screen.getAllByTestId('mapbox-marker');
    expect(markers).toHaveLength(mockCars.length + mockServiceStations.length);
  });

  it('renders GeoJSON polygon layers', () => {
    render(<RealtimeMapView {...defaultProps} />);
    expect(screen.getByTestId('mapbox-source')).toBeInTheDocument();
    expect(screen.getByTestId('mapbox-layer')).toBeInTheDocument();
  });

  it('displays car information in markers', () => {
    render(<RealtimeMapView {...defaultProps} />);
    // Check that car IDs are displayed
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('displays service station queue lengths', () => {
    render(<RealtimeMapView {...defaultProps} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('highlights selected car', () => {
    const props = { ...defaultProps, selectedCarId: 1 };
    render(<RealtimeMapView {...props} />);

    // The selected car marker should have different styling
    // This would require more detailed testing of the marker content
    const markers = screen.getAllByTestId('mapbox-marker');
    expect(markers.length).toBeGreaterThan(0);
  });

  it('calls onCarSelect when car marker is clicked', () => {
    const mockOnCarSelect = jest.fn();
    const props = { ...defaultProps, onCarSelect: mockOnCarSelect };
    render(<RealtimeMapView {...props} />);

    const markers = screen.getAllByTestId('mapbox-marker');
    // Click on first car marker (assuming order)
    fireEvent.click(markers[0]);

    expect(mockOnCarSelect).toHaveBeenCalledWith(1);
  });

  it('renders time speed control', () => {
    render(<RealtimeMapView {...defaultProps} />);
    const select = screen.getByDisplayValue('1');
    expect(select).toBeInTheDocument();
  });

  it('calls onTimeSpeedChange when speed is changed', () => {
    const mockOnTimeSpeedChange = jest.fn();
    const props = { ...defaultProps, onTimeSpeedChange: mockOnTimeSpeedChange };
    render(<RealtimeMapView {...props} />);

    const select = screen.getByDisplayValue('1');
    fireEvent.change(select, { target: { value: '2' } });

    expect(mockOnTimeSpeedChange).toHaveBeenCalledWith(2);
  });

  it('handles missing GeoJSON polygon', () => {
    const props = { ...defaultProps, geoJsonPolygon: undefined };
    render(<RealtimeMapView {...props} />);

    // Should not render source/layer when no polygon
    expect(screen.queryByTestId('mapbox-source')).not.toBeInTheDocument();
  });

  it('handles empty service stations array', () => {
    const props = { ...defaultProps, serviceStations: [] };
    render(<RealtimeMapView {...props} />);

    const markers = screen.getAllByTestId('mapbox-marker');
    // Should only have car markers
    expect(markers).toHaveLength(mockCars.length);
  });

  it('handles empty cars array', () => {
    const props = { ...defaultProps, cars: [] };
    render(<RealtimeMapView {...props} />);

    const markers = screen.getAllByTestId('mapbox-marker');
    // Should only have station markers
    expect(markers).toHaveLength(mockServiceStations.length);
  });
});