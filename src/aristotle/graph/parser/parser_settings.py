class ParserSettings:
    def __init__(
        self,
        include_private_dirs: bool = False,
        include_test_files: bool = False,
        include_private_members: bool = False,
        include_dunder: bool = True,
        include_module_name: bool = True,
    ):
        """
        Args:
            include_private_dirs: Whether to include dirs starting with "_"
            include_test_files: Whether to include dirs starting with "test_"
            include_private: Whether to include private members (starting with "_")
            include_dunder: Whether to include dunder methods (starting and ending with "__")
            include_module_name: Whether to include module name in the namespace hierarchy
        """
        self.include_private_dirs = include_private_dirs
        self.include_test_files = include_test_files
        self.include_private_members = include_private_members
        self.include_dunder = include_dunder
        self.include_module_name = include_module_name
