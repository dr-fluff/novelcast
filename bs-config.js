/* bs-config.js */
require("dotenv").config();

module.exports = {
    proxy: {
        target: `http://localhost:${process.env.PORT || 8001}`,
        ws: true,
    },
    files: ["src/**/*.html", "src/**/*.css"],
    port: 3000,
    open: false,
    notify: false
};