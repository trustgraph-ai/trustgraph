// Parameter Processing Module
// Handles dynamic parameter replacement in configuration values
// Replaces {parameter_name} placeholders with actual parameter values

{
    // Applies parameter substitutions to string values
    // Only processes strings - leaves other types unchanged
    substitute_parameters: function(value, parameters)
        if std.isString(value) then
            std.foldl(
                function(acc, param)
                    // Only do string replacement if param.value is a string
                    if std.isString(param.value) then
                        std.strReplace(acc, "{" + param.key + "}", param.value)
                    else
                        acc,  // Skip replacement for non-string parameter values
                std.objectKeysValuesAll(parameters),
                value
            )
        else
            value,

    // Applies parameter substitutions to all values in an object
    // Recursively processes nested objects and arrays
    substitute_parameters_in_object: function(obj, parameters)
        if std.isObject(obj) then
            {
                [key]: $.substitute_parameters_in_object(obj[key], parameters)
                for key in std.objectFields(obj)
            }
        else if std.isArray(obj) then
            [
                $.substitute_parameters_in_object(item, parameters)
                for item in obj
            ]
        else
            $.substitute_parameters(obj, parameters),
}