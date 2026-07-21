# 自动化测试框架

## 项目测试结构

```
tests/
├── conftest.py              # pytest 配置和共享fixtures
├── test_config_manager.py   # 配置管理器测试 (14个测试)
├── test_exceptions.py       # 异常系统测试 (21个测试)
├── test_pipeline.py         # 处理器管道测试 (14个测试)
├── test_lut_filters.py      # LUT滤镜测试 (27个测试)
├── test_options_manager.py  # 选项管理器测试 (34个测试)
├── test_app_data_paths.py   # 应用数据路径测试 (19个测试)
└── pytest.ini              # pytest 配置文件

总计: 129+ 个单元测试
```

## 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_config_manager.py -v

# 运行特定测试类
python -m pytest tests/test_exceptions.py::TestVideoProcessException -v

# 生成覆盖率报告
python -m pytest tests/ --cov=utils --cov=config --cov=processor --cov-report=html
```

## 测试覆盖范围

### 1. 配置系统测试 (test_config_manager.py)
- UIConfig 默认值和自定义值
- VideoProcessConfig 和子配置对象
- AudioConfig 音频配置
- AIConfig AI功能和设备选项
- ConfigManager 单例模式、保存/加载、验证
- 全局配置管理器函数

### 2. 异常系统测试 (test_exceptions.py)
- VideoProcessException 基类
- ValidationException 验证异常
- ProcessorException 处理器异常
- IOException IO异常
- ConfigException 配置异常
- ResourceException 资源异常
- 异常继承关系和用法

### 3. 管道系统测试 (test_pipeline.py)
- ProcessingData 数据类
- ProcessorPipeline 链式执行
- 处理器成功/失败场景
- 数据流和独立性
- 异常处理

### 4. LUT滤镜测试 (test_lut_filters.py)
- 滤镜定义完整性
- 唯一性检查
- 路径解析
- 名称映射

### 5. 选项管理器测试 (test_options_manager.py)
- INI配置读写
- 裂变、GPU、输出配置
- 批处理选项
- UI和性能配置

### 6. 应用路径测试 (test_app_data_paths.py)
- 用户数据目录创建
- 环境变量回退
- 路径格式和组件

## 添加新测试

```python
# tests/test_new_feature.py
def test_new_feature():
    """测试新功能"""
    from module import new_function
    result = new_function()
    assert result == expected_value
```

## 依赖安装

```bash
pip install pytest pytest-mock
```
