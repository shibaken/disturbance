var merge = require('webpack-merge')
var prodEnv = require('./prod.env')

module.exports = merge(prodEnv, {
  NODE_ENV: '"development"',
  //WEBPACK_HOST: '"172.31.1.50:8080"',
  // WEBPACK_HOST: '"localhost:8080"',
  // PORT: '"8080"'
  WEBPACK_HOST: '"localhost:9062"',
  PORT: '"9062"'
})
