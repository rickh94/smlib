const purgecss = require('@fullhuman/postcss-purgecss')({
  content: ['../templates/*.html', '../templates/**/*.html'],
  defaultExtractor: content => content.match(/[\w-/:]+(?<!:)/g) || [],
});

module.exports = {
  plugins: [
    require('tailwindcss'),
    require('autoprefixer'),
    require('postcss-import'),
    ...(process.env.NODE_ENV === 'production' ? [purgecss] : []),
  ],
};
