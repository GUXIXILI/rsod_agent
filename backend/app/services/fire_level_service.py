"""
火情等级判定服务

根据检测到的火焰面积、烟雾面积和目标数量，判定火情等级：
- safe：安全，无火焰且烟雾面积占比 < 5%
- notice：关注，有烟雾但无火焰，烟雾面积 >= 5%
- warning：警告，有火焰或烟雾面积较大
- danger：危险，火焰面积大或火焰目标多
"""


class FireLevelService:
    """火情等级判定服务"""

    def judge(
        self,
        fire_count: int = 0,
        smoke_count: int = 0,
        fire_area: float = 0.0,
        smoke_area: float = 0.0,
    ) -> dict:
        """
        根据检测结果判定火情等级

        Args:
            fire_count: 火焰目标数量
            smoke_count: 烟雾目标数量
            fire_area: 火焰面积占比 0~1
            smoke_area: 烟雾面积占比 0~1

        Returns:
            dict: {
                "fire_level": "safe"|"notice"|"warning"|"danger",
                "fire_area": float,
                "smoke_area": float,
                "fire_object_count": int,
                "smoke_object_count": int,
                "suggestion": str
            }
        """
        # 等级判定规则
        if fire_area > 0.1 or fire_count >= 3:
            level = "danger"
        elif fire_area > 0.03 or fire_count >= 1:
            level = "warning"
        elif smoke_area > 0.05 or smoke_count >= 2:
            level = "notice"
        else:
            level = "safe"

        suggestions = {
            "safe": "当前无火情，持续监控中",
            "notice": "检测到烟雾，持续观察，确认是否为误报",
            "warning": "检测到火焰，立即现场核实，准备灭火设备",
            "danger": "火势较大，立即拨打119，启动消防喷淋，组织人员疏散，切断电源和燃气",
        }

        return {
            "fire_level": level,
            "fire_area": fire_area,
            "smoke_area": smoke_area,
            "fire_object_count": fire_count,
            "smoke_object_count": smoke_count,
            "suggestion": suggestions.get(level, ""),
        }


# 单例
fire_level_service = FireLevelService()