required_versions = {
    "Flask": "2.3.3",
    "Flask_Admin": "1.6.1",
    "Flask_Cors": "4.0.0",
    "Flask_Login": "0.6.3",
    "flask_sqlalchemy": "3.1.1",
    "mysql_connector_repackaged": "0.3.1",
    "Requests": "2.31.0",
    "SQLAlchemy": "2.0.23",
    "Werkzeug": "2.3.7"
}

import pkg_resources

for pkg, required_version in required_versions.items():
    try:
        installed_version = pkg_resources.get_distribution(pkg).version
        if installed_version == required_version:
            print(f"{pkg} ✅ Version matches: {installed_version}")
        else:
            print(f"{pkg} ⚠️ Installed: {installed_version}, Required: {required_version}")
    except pkg_resources.DistributionNotFound:
        print(f"{pkg} ❌ Not installed")
