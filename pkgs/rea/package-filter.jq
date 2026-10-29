# No lifecycle installers or optional Frida acquisition in the immutable package.
del(.devDependencies, .optionalDependencies, .allowScripts, .scripts)
