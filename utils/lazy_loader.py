# -*- coding: utf-8 -*-
"""
懒加载模块 - 延迟加载重型处理器和模块
用于优化启动性能
"""


class LazyLoader:
    """懒加载装饰器 - 延迟加载重型模块"""
    
    def __init__(self, module_path, class_name):
        """
        初始化懒加载器
        
        Args:
            module_path: 模块路径，如 'processor.ai_processor'
            class_name: 类名，如 'AIProcessor'
        """
        self.module_path = module_path
        self.class_name = class_name
        self._instance = None
        self._class = None
    
    def _load_class(self):
        """加载类"""
        if self._class is None:
            try:
                module = __import__(self.module_path, fromlist=[self.class_name])
                self._class = getattr(module, self.class_name)
            except ImportError as e:
                raise ImportError(f"无法导入 {self.module_path}.{self.class_name}: {str(e)}")
            except AttributeError as e:
                raise AttributeError(f"类 {self.class_name} 在模块 {self.module_path} 中不存在: {str(e)}")
        return self._class
    
    def __call__(self, *args, **kwargs):
        """
        首次调用时加载类并创建实例
        后续调用返回相同的实例
        """
        if self._instance is None:
            cls = self._load_class()
            self._instance = cls(*args, **kwargs)
        return self._instance
    
    def __getattr__(self, name):
        """代理属性访问"""
        if self._instance is None:
            cls = self._load_class()
            self._instance = cls()
        return getattr(self._instance, name)


class LazyProperty:
    """属性级别的懒加载"""
    
    def __init__(self, factory):
        """
        初始化懒属性
        
        Args:
            factory: 创建对象的工厂函数
        """
        self.factory = factory
        self.value = None
        self.loaded = False
    
    def get(self):
        """获取值，首次调用时创建"""
        if not self.loaded:
            self.value = self.factory()
            self.loaded = True
        return self.value
    
    def reset(self):
        """重置，下次访问会重新创建"""
        self.value = None
        self.loaded = False
