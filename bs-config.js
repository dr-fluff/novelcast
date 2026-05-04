/* bs-config.js */
require("dotenv").config();
    module.exports = {
    proxy: `http://localhost:${process.env.PORT || 8001}`,
    files: ["src/**/*.html", "src/**/*.css"],
    port: 3000,
    open: false,
    notify: false
};
