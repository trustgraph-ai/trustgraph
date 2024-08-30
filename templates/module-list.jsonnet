
local all = import "all-patterns.jsonnet";

std.foldl(
    function(m, p) m + { [p.pattern.name]: p.module},
    all,
    {}
)

