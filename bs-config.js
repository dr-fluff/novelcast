require("dotenv").config();
    module.exports = {
    proxy: `http://localhost:${process.env.port || 8001}`,
    files: ["src/**/*.html", "src/**/*.css"],
    port: 3000,
    open: false,
    notify: false
};
