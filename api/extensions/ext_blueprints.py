from configs import dify_config
from dify_app import DifyApp


def init_app(app: DifyApp):
    # register blueprint routers

    from flask_cors import CORS  # type: ignore

    from controllers.console import bp as console_app_bp
    from controllers.files import bp as files_bp
    from controllers.inner_api import bp as inner_api_bp
    from controllers.service_api import bp as service_api_bp
    from controllers.web import bp as web_bp

    #------------------------------------------------------------------------------
    # CODELIGHT_CUSTOMIZATION: Register Codelight blueprint
    # Version: 1.0.0
    # Author: Codelight - Lau Truong
    # Date: 2025-03-14
    #
    # Description: This line registers the custom Codelight blueprint with the
    # Flask application. The blueprint contains all Codelight-specific routes
    # and API endpoints, keeping them organized separately from the core
    # of customizations.
    #------------------------------------------------------------------------------
    from controllers.codelight import bp as codelight_bp

    CORS(
        service_api_bp,
        allow_headers=["Content-Type", "Authorization", "X-App-Code"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    )
    app.register_blueprint(service_api_bp)

    CORS(
        web_bp,
        resources={r"/*": {"origins": dify_config.WEB_API_CORS_ALLOW_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-App-Code"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["X-Version", "X-Env"],
    )

    app.register_blueprint(web_bp)

    CORS(
        console_app_bp,
        resources={r"/*": {"origins": dify_config.CONSOLE_CORS_ALLOW_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["X-Version", "X-Env"],
    )

    app.register_blueprint(console_app_bp)

    CORS(files_bp, allow_headers=["Content-Type"], methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"])
    app.register_blueprint(files_bp)

    #------------------------------------------------------------------------------
    # CODELIGHT_CUSTOMIZATION: Register and configure Codelight blueprint
    # Version: 1.0.0
    # Author: Codelight - Lau Truong
    # Date: 2025-03-14
    #
    # Description: This section registers the Codelight blueprint with the Flask
    # application and configures CORS (Cross-Origin Resource Sharing) for it.
    # The CORS configuration allows specific HTTP methods and headers needed for
    # the Codelight frontend to communicate with these custom API endpoints.
    # Note: The blueprint is registered twice, which may be a mistake that should
    # be reviewed.
    #------------------------------------------------------------------------------
    CORS(
        codelight_bp,
        allow_headers=["Content-Type", "Authorization", "X-App-Code"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    )
    app.register_blueprint(codelight_bp)

