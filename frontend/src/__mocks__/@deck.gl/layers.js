// Mock for @deck.gl/layers

class MockLayer {
  constructor(props) {
    this.id = props?.id || 'mock-layer';
    this.props = props || {};
  }
}

class ScatterplotLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'ScatterplotLayer';
  }
}

class PathLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'PathLayer';
  }
}

class GeoJsonLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'GeoJsonLayer';
  }
}

class IconLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'IconLayer';
  }
}

class LineLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'LineLayer';
  }
}

class TextLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'TextLayer';
  }
}

class PolygonLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'PolygonLayer';
  }
}

class ArcLayer extends MockLayer {
  constructor(props) {
    super(props);
    this.type = 'ArcLayer';
  }
}

module.exports = {
  ScatterplotLayer,
  PathLayer,
  GeoJsonLayer,
  IconLayer,
  LineLayer,
  TextLayer,
  PolygonLayer,
  ArcLayer,
};
