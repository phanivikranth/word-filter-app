const fs = require('fs');
const path = require('path');

const distDir = path.join(__dirname, '../dist/word-filter-frontend');
const index = path.join(distDir, 'index.html');
const notFound = path.join(distDir, '404.html');

fs.copyFileSync(index, notFound);
console.log('Copied index.html to 404.html for SPA hosting');
