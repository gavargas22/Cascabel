// Mock for @deck.gl/react
const React = require('react');

const DeckGL = React.forwardRef((props, ref) => {
  const { layers, children, ...rest } = props;
  return React.createElement(
    'div',
    {
      'data-testid': 'mock-deckgl',
      'data-layer-count': layers?.length || 0,
      ref,
      ...rest,
    },
    children
  );
});

DeckGL.displayName = 'DeckGL';

module.exports = {
  DeckGL,
  default: DeckGL,
};
