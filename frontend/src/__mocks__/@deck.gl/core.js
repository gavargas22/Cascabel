// Mock for @deck.gl/core
class Layer {
  constructor(props) {
    this.props = props;
  }
}

class CompositeLayer extends Layer {}

class Deck {
  constructor(props) {
    this.props = props;
  }
  setProps(props) {
    this.props = { ...this.props, ...props };
  }
  finalize() {}
}

module.exports = {
  Layer,
  CompositeLayer,
  Deck,
  COORDINATE_SYSTEM: {
    LNGLAT: 1,
    METER_OFFSETS: 2,
  },
  log: {
    level: 0,
    enable: jest.fn(),
  },
};
