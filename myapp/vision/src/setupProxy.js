const { createProxyMiddleware } = require('http-proxy-middleware');

// https://create-react-app.dev/docs/proxying-api-requests-in-development/
module.exports = function (app) {
    app.use(
        ['**/api/**', '/myapp', '**/list/**'],
        createProxyMiddleware({
            target: 'http://localhost',
            changeOrigin: true,
        })
    );
};