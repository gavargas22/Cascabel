// Mock for @deck.gl/mapbox

class MapboxOverlay {
  constructor(props) {
    this.props = props || {};
    this._deck = null;
  }

  setProps(props) {
    this.props = { ...this.props, ...props };
  }

  onAdd(map) {
    this._map = map;
    return document.createElement('div');
  }

  onRemove() {
    this._map = null;
  }

  getDefaultPosition() {
    return 'top-left';
  }
}

class MapboxLayer {
  constructor(props) {
    this.id = props?.id || 'mapbox-layer';
    this.props = props || {};
  }
}

module.exports = {
  MapboxOverlay,
  MapboxLayer,
};
