"""
火情等级判定服务单元测试
覆盖 safe / notice / warning / danger 四个等级及边界条件
"""
import pytest

from app.services.fire_level_service import FireLevelService, fire_level_service


class TestFireLevelSafe:
    """safe 等级测试"""

    def test_no_fire_no_smoke(self):
        """无火焰无烟雾 → safe"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.0, smoke_area=0.0)
        assert result["fire_level"] == "safe"
        assert "无火情" in result["suggestion"]

    def test_small_smoke_below_threshold(self):
        """烟雾面积 < 5% 且无火焰 → safe"""
        result = fire_level_service.judge(fire_count=0, smoke_count=1, fire_area=0.0, smoke_area=0.04)
        assert result["fire_level"] == "safe"

    def test_smoke_count_one_below_threshold(self):
        """烟雾目标数 1（< 2）且面积不超标 → safe"""
        result = fire_level_service.judge(fire_count=0, smoke_count=1, fire_area=0.0, smoke_area=0.0)
        assert result["fire_level"] == "safe"


class TestFireLevelNotice:
    """notice 等级测试"""

    def test_smoke_area_above_threshold(self):
        """烟雾面积 >= 5% 且无火焰 → notice"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.0, smoke_area=0.06)
        assert result["fire_level"] == "notice"
        assert "烟雾" in result["suggestion"]

    def test_smoke_area_exact_boundary(self):
        """烟雾面积刚好 0.051（> 0.05）→ notice"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.0, smoke_area=0.051)
        assert result["fire_level"] == "notice"

    def test_smoke_count_two_triggers_notice(self):
        """烟雾目标数 = 2 → notice"""
        result = fire_level_service.judge(fire_count=0, smoke_count=2, fire_area=0.0, smoke_area=0.0)
        assert result["fire_level"] == "notice"

    def test_smoke_area_exact_005(self):
        """烟雾面积刚好 0.05（不大于）→ safe"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.0, smoke_area=0.05)
        assert result["fire_level"] == "safe"


class TestFireLevelWarning:
    """warning 等级测试"""

    def test_small_fire_area(self):
        """火焰面积 0.04（> 0.03 且 <= 0.1）→ warning"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.04, smoke_area=0.0)
        assert result["fire_level"] == "warning"
        assert "火焰" in result["suggestion"]

    def test_fire_count_one(self):
        """火焰目标数 = 1 → warning"""
        result = fire_level_service.judge(fire_count=1, smoke_count=0, fire_area=0.0, smoke_area=0.0)
        assert result["fire_level"] == "warning"

    def test_fire_area_exact_003(self):
        """火焰面积刚好 0.03（不大于 0.03）且无火焰目标 → safe（不触发 warning）"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.03, smoke_area=0.0)
        # 0.03 is NOT > 0.03, and fire_count=0 < 1 → falls through to safe/notice check
        assert result["fire_level"] == "safe"

    def test_fire_area_just_above_003(self):
        """火焰面积 0.031（> 0.03）→ warning"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.031, smoke_area=0.0)
        assert result["fire_level"] == "warning"

    def test_fire_count_two(self):
        """火焰目标数 = 2 但面积不大 → warning"""
        result = fire_level_service.judge(fire_count=2, smoke_count=0, fire_area=0.01, smoke_area=0.0)
        assert result["fire_level"] == "warning"


class TestFireLevelDanger:
    """danger 等级测试"""

    def test_large_fire_area(self):
        """火焰面积 > 0.1 → danger"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.15, smoke_area=0.0)
        assert result["fire_level"] == "danger"
        assert "119" in result["suggestion"]

    def test_fire_area_exact_01(self):
        """火焰面积刚好 0.1（不大于 0.1）→ warning，不是 danger"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.1, smoke_area=0.0)
        assert result["fire_level"] == "warning"

    def test_fire_area_just_above_01(self):
        """火焰面积 0.101（> 0.1）→ danger"""
        result = fire_level_service.judge(fire_count=0, smoke_count=0, fire_area=0.101, smoke_area=0.0)
        assert result["fire_level"] == "danger"

    def test_fire_count_three(self):
        """火焰目标数 = 3 → danger"""
        result = fire_level_service.judge(fire_count=3, smoke_count=0, fire_area=0.0, smoke_area=0.0)
        assert result["fire_level"] == "danger"

    def test_fire_count_five_large_area(self):
        """多个火焰目标 + 大面积 → danger"""
        result = fire_level_service.judge(fire_count=5, smoke_count=3, fire_area=0.3, smoke_area=0.2)
        assert result["fire_level"] == "danger"


class TestFireLevelReturnValue:
    """返回值结构完整性测试"""

    def test_return_dict_keys(self):
        """返回 dict 包含所有必要字段"""
        result = fire_level_service.judge(fire_count=1, smoke_count=1, fire_area=0.05, smoke_area=0.06)
        assert "fire_level" in result
        assert "fire_area" in result
        assert "smoke_area" in result
        assert "fire_object_count" in result
        assert "smoke_object_count" in result
        assert "suggestion" in result

    def test_return_values_match_input(self):
        """返回值中 fire_area/smoke_area/count 与输入一致"""
        result = fire_level_service.judge(fire_count=2, smoke_count=3, fire_area=0.12, smoke_area=0.08)
        assert result["fire_area"] == 0.12
        assert result["smoke_area"] == 0.08
        assert result["fire_object_count"] == 2
        assert result["smoke_object_count"] == 3

    def test_singleton_instance(self):
        """fire_level_service 为单例"""
        from app.services.fire_level_service import fire_level_service as another_ref
        assert fire_level_service is another_ref

    def test_class_instantiation(self):
        """可以直接实例化 FireLevelService"""
        svc = FireLevelService()
        result = svc.judge(fire_count=0, smoke_count=0, fire_area=0.0, smoke_area=0.0)
        assert result["fire_level"] == "safe"
