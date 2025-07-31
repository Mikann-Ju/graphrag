#!/usr/bin/env python3
"""
游戏数据生成器
为GraphRAG游戏智能分析项目生成模拟数据
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Tuple
import uuid


class GameDataGenerator:
    """游戏数据生成器"""
    
    def __init__(self, seed: int = 42):
        """初始化数据生成器"""
        random.seed(seed)
        np.random.seed(seed)
        
        # 游戏配置
        self.game_types = ["消消乐", "纸牌", "桌球", "麻将"]
        self.room_types = ["免费场", "付费场", "高级付费场"]
        self.player_segments = ["新手", "活跃", "重度", "VIP"]
        
        # 时间范围
        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2024, 3, 31)
        
    def generate_players(self, num_players: int = 10000) -> pd.DataFrame:
        """生成玩家数据"""
        
        players = []
        
        for i in range(num_players):
            # 基础信息
            player_id = f"player_{i+1:06d}"
            registration_date = self._random_date(self.start_date, self.end_date - timedelta(days=30))
            
            # 玩家类型分布
            segment = np.random.choice(self.player_segments, p=[0.4, 0.35, 0.2, 0.05])
            
            # 根据玩家类型生成特征
            if segment == "新手":
                total_spending = round(np.random.exponential(10), 2)
                total_sessions = np.random.randint(1, 20)
                avg_session_duration = np.random.randint(5, 30)
                churn_risk = np.random.uniform(0.3, 0.8)
            elif segment == "活跃":
                total_spending = round(np.random.exponential(50), 2)
                total_sessions = np.random.randint(20, 100)
                avg_session_duration = np.random.randint(15, 60)
                churn_risk = np.random.uniform(0.1, 0.4)
            elif segment == "重度":
                total_spending = round(np.random.exponential(200), 2)
                total_sessions = np.random.randint(100, 500)
                avg_session_duration = np.random.randint(30, 120)
                churn_risk = np.random.uniform(0.05, 0.3)
            else:  # VIP
                total_spending = round(np.random.exponential(1000), 2)
                total_sessions = np.random.randint(200, 1000)
                avg_session_duration = np.random.randint(45, 180)
                churn_risk = np.random.uniform(0.02, 0.2)
            
            # 最后活跃时间
            last_active = self._random_date(
                registration_date + timedelta(days=1),
                self.end_date
            )
            
            # 偏好的游戏类型和场次类型
            preferred_game = random.choice(self.game_types)
            preferred_room = np.random.choice(
                self.room_types, 
                p=[0.5, 0.35, 0.15] if segment in ["新手", "活跃"] else [0.2, 0.4, 0.4]
            )
            
            # 投资风格
            if total_spending / max(total_sessions, 1) < 1:
                investment_style = "保守型"
            elif total_spending / max(total_sessions, 1) > 5:
                investment_style = "激进型"
            else:
                investment_style = "平衡型"
            
            player = {
                "player_id": player_id,
                "registration_date": registration_date.strftime("%Y-%m-%d"),
                "last_active_date": last_active.strftime("%Y-%m-%d"),
                "segment": segment,
                "total_spending": total_spending,
                "total_sessions": total_sessions,
                "avg_session_duration_minutes": avg_session_duration,
                "preferred_game_type": preferred_game,
                "preferred_room_type": preferred_room,
                "investment_style": investment_style,
                "churn_risk_score": round(churn_risk, 3),
                "level": np.random.randint(1, 101),
                "country": random.choice(["中国", "美国", "日本", "韩国", "新加坡"]),
                "device_type": random.choice(["iOS", "Android", "Web"])
            }
            
            players.append(player)
        
        return pd.DataFrame(players)
    
    def generate_rooms(self, num_rooms: int = 100) -> pd.DataFrame:
        """生成场次数据"""
        
        rooms = []
        
        for i in range(num_rooms):
            room_id = f"room_{i+1:03d}"
            room_type = random.choice(self.room_types)
            game_type = random.choice(self.game_types)
            
            # 根据场次类型设置门槛费和奖池
            if room_type == "免费场":
                entry_fee = 0.0
                base_prize = np.random.uniform(10, 50)
            elif room_type == "付费场":
                entry_fee = round(np.random.uniform(1, 10), 2)
                base_prize = entry_fee * np.random.uniform(2, 5)
            else:  # 高级付费场
                entry_fee = round(np.random.uniform(10, 100), 2)
                base_prize = entry_fee * np.random.uniform(1.5, 3)
            
            # 参与统计
            total_participants = np.random.randint(100, 10000)
            avg_daily_participants = total_participants // 90  # 90天数据
            
            # 满意度评分
            if room_type == "免费场":
                satisfaction_score = np.random.uniform(0.6, 0.8)
            elif room_type == "付费场":
                satisfaction_score = np.random.uniform(0.7, 0.9)
            else:
                satisfaction_score = np.random.uniform(0.8, 0.95)
            
            room = {
                "room_id": room_id,
                "room_type": room_type,
                "game_type": game_type,
                "entry_fee": entry_fee,
                "base_prize_pool": round(base_prize, 2),
                "total_participants": total_participants,
                "avg_daily_participants": avg_daily_participants,
                "satisfaction_score": round(satisfaction_score, 3),
                "min_level_required": np.random.randint(1, 50),
                "max_players_per_session": random.choice([4, 6, 8, 10]),
                "avg_session_duration_minutes": np.random.randint(10, 60),
                "win_rate_target": round(np.random.uniform(0.15, 0.35), 3),
                "created_date": self._random_date(self.start_date, self.start_date + timedelta(days=30)).strftime("%Y-%m-%d")
            }
            
            rooms.append(room)
        
        return pd.DataFrame(rooms)
    
    def generate_game_sessions(self, players_df: pd.DataFrame, rooms_df: pd.DataFrame, 
                             num_sessions: int = 50000) -> pd.DataFrame:
        """生成游戏会话数据"""
        
        sessions = []
        
        for i in range(num_sessions):
            session_id = f"session_{i+1:08d}"
            
            # 选择玩家和房间
            player = players_df.sample(1).iloc[0]
            
            # 根据玩家偏好选择房间
            if random.random() < 0.7:  # 70%概率选择偏好类型
                available_rooms = rooms_df[rooms_df['room_type'] == player['preferred_room_type']]
                if len(available_rooms) == 0:
                    room = rooms_df.sample(1).iloc[0]
                else:
                    room = available_rooms.sample(1).iloc[0]
            else:
                room = rooms_df.sample(1).iloc[0]
            
            # 会话时间
            session_start = self._random_date(
                datetime.strptime(player['registration_date'], "%Y-%m-%d"),
                datetime.strptime(player['last_active_date'], "%Y-%m-%d")
            )
            
            duration = np.random.poisson(room['avg_session_duration_minutes'])
            session_end = session_start + timedelta(minutes=max(duration, 5))
            
            # 游戏结果
            is_winner = random.random() < room['win_rate_target']
            
            # 计算奖励
            if is_winner:
                reward = room['base_prize_pool'] * np.random.uniform(0.8, 1.2)
            else:
                reward = 0
            
            # 计算投资回报比
            if room['entry_fee'] > 0:
                roi_ratio = reward / room['entry_fee']
            else:
                roi_ratio = float('inf') if reward > 0 else 0
            
            # 玩家满意度（基于ROI和游戏体验）
            base_satisfaction = room['satisfaction_score']
            if roi_ratio > 1.5:
                satisfaction_rating = min(base_satisfaction + 0.2, 1.0)
            elif roi_ratio < 0.5:
                satisfaction_rating = max(base_satisfaction - 0.3, 0.1)
            else:
                satisfaction_rating = base_satisfaction + np.random.uniform(-0.1, 0.1)
            
            session = {
                "session_id": session_id,
                "player_id": player['player_id'],
                "room_id": room['room_id'],
                "session_start_time": session_start.strftime("%Y-%m-%d %H:%M:%S"),
                "session_end_time": session_end.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_minutes": (session_end - session_start).seconds // 60,
                "entry_fee_paid": room['entry_fee'],
                "reward_received": round(reward, 2),
                "is_winner": is_winner,
                "roi_ratio": round(roi_ratio, 3) if roi_ratio != float('inf') else 999,
                "satisfaction_rating": round(satisfaction_rating, 3),
                "game_score": np.random.randint(100, 10000),
                "moves_made": np.random.randint(20, 200),
                "power_ups_used": np.random.randint(0, 10),
                "opponents_defeated": np.random.randint(0, room['max_players_per_session']-1)
            }
            
            sessions.append(session)
        
        return pd.DataFrame(sessions)
    
    def generate_payment_records(self, sessions_df: pd.DataFrame) -> pd.DataFrame:
        """生成付费记录"""
        
        # 筛选出有付费的会话
        paid_sessions = sessions_df[sessions_df['entry_fee_paid'] > 0].copy()
        
        payments = []
        
        for _, session in paid_sessions.iterrows():
            payment_id = f"payment_{len(payments)+1:08d}"
            
            # 付费时间（会话开始前几分钟）
            session_start = datetime.strptime(session['session_start_time'], "%Y-%m-%d %H:%M:%S")
            payment_time = session_start - timedelta(minutes=np.random.randint(1, 10))
            
            # 付费方式
            payment_method = random.choice(["微信支付", "支付宝", "信用卡", "Apple Pay", "Google Pay"])
            
            # 付费状态
            payment_status = random.choice(["成功", "成功", "成功", "成功", "失败"])  # 80%成功率
            
            if payment_status == "成功":
                actual_amount = session['entry_fee_paid']
            else:
                actual_amount = 0
            
            payment = {
                "payment_id": payment_id,
                "session_id": session['session_id'],
                "player_id": session['player_id'],
                "room_id": session['room_id'],
                "payment_time": payment_time.strftime("%Y-%m-%d %H:%M:%S"),
                "amount": session['entry_fee_paid'],
                "actual_amount": actual_amount,
                "payment_method": payment_method,
                "payment_status": payment_status,
                "currency": "CNY",
                "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
                "refund_amount": 0.0,
                "roi_achieved": session['roi_ratio'],
                "satisfaction_post_payment": session['satisfaction_rating']
            }
            
            payments.append(payment)
        
        return pd.DataFrame(payments)
    
    def generate_text_documents(self, players_df: pd.DataFrame, rooms_df: pd.DataFrame, 
                              sessions_df: pd.DataFrame, payments_df: pd.DataFrame) -> pd.DataFrame:
        """生成用于GraphRAG的文本文档"""
        
        documents = []
        doc_id = 1
        
        # 1. 玩家画像文档
        for _, player in players_df.iterrows():
            player_sessions = sessions_df[sessions_df['player_id'] == player['player_id']]
            player_payments = payments_df[payments_df['player_id'] == player['player_id']]
            
            text = f"""
            玩家档案：{player['player_id']}
            
            基本信息：
            - 注册时间：{player['registration_date']}
            - 玩家等级：{player['level']}
            - 玩家类型：{player['segment']}
            - 设备类型：{player['device_type']}
            - 所在地区：{player['country']}
            
            游戏偏好：
            - 偏好游戏类型：{player['preferred_game_type']}
            - 偏好场次类型：{player['preferred_room_type']}
            - 投资风格：{player['investment_style']}
            
            行为数据：
            - 总游戏场次：{player['total_sessions']}场
            - 平均每场时长：{player['avg_session_duration_minutes']}分钟
            - 总消费金额：{player['total_spending']}元
            - 流失风险评分：{player['churn_risk_score']}
            
            最近活动：
            - 最后活跃时间：{player['last_active_date']}
            - 参与场次数量：{len(player_sessions)}
            - 付费次数：{len(player_payments)}
            - 平均投资回报率：{player_sessions['roi_ratio'].mean():.2f}
            
            风险评估：
            {'该玩家流失风险较高，需要重点关注' if player['churn_risk_score'] > 0.6 else '该玩家活跃度良好，可适当推荐高级场次' if player['churn_risk_score'] < 0.3 else '该玩家状态稳定，建议维持当前运营策略'}
            """
            
            documents.append({
                "id": f"player_profile_{doc_id:06d}",
                "text": text.strip(),
                "metadata": json.dumps({
                    "document_type": "player_profile",
                    "player_id": player['player_id'],
                    "segment": player['segment'],
                    "churn_risk": player['churn_risk_score'],
                    "total_spending": player['total_spending']
                })
            })
            doc_id += 1
        
        # 2. 场次分析文档
        for _, room in rooms_df.iterrows():
            room_sessions = sessions_df[sessions_df['room_id'] == room['room_id']]
            room_payments = payments_df[payments_df['room_id'] == room['room_id']]
            
            if len(room_sessions) > 0:
                avg_roi = room_sessions['roi_ratio'].mean()
                win_rate = room_sessions['is_winner'].mean()
                avg_satisfaction = room_sessions['satisfaction_rating'].mean()
                total_revenue = room_payments['actual_amount'].sum()
                
                text = f"""
                场次分析报告：{room['room_id']}
                
                场次基本信息：
                - 场次类型：{room['room_type']}
                - 游戏类型：{room['game_type']}
                - 门槛费：{room['entry_fee']}元
                - 基础奖池：{room['base_prize_pool']}元
                - 创建时间：{room['created_date']}
                
                运营数据：
                - 总参与人次：{len(room_sessions)}
                - 平均每日参与人数：{room['avg_daily_participants']}
                - 实际胜率：{win_rate:.2%}
                - 目标胜率：{room['win_rate_target']:.2%}
                - 平均投资回报率：{avg_roi:.2f}
                
                收益分析：
                - 总收入：{total_revenue:.2f}元
                - 平均场次收入：{total_revenue/max(len(room_sessions), 1):.2f}元
                - 玩家满意度：{avg_satisfaction:.2f}/1.0
                
                优化建议：
                {'建议降低门槛费或增加奖池吸引更多玩家' if avg_satisfaction < 0.6 else '建议适当增加门槛费提升收益' if avg_satisfaction > 0.9 else '当前配置比较合理，建议保持'}
                
                风险因素：
                {'胜率过低，可能影响玩家体验' if win_rate < room['win_rate_target'] * 0.8 else '胜率过高，可能影响收益' if win_rate > room['win_rate_target'] * 1.5 else '胜率控制在合理范围内'}
                """
                
                documents.append({
                    "id": f"room_analysis_{doc_id:06d}",
                    "text": text.strip(),
                    "metadata": json.dumps({
                        "document_type": "room_analysis", 
                        "room_id": room['room_id'],
                        "room_type": room['room_type'],
                        "total_revenue": float(total_revenue),
                        "avg_satisfaction": float(avg_satisfaction),
                        "participant_count": len(room_sessions)
                    })
                })
                doc_id += 1
        
        # 3. 付费行为分析文档
        for player_id in payments_df['player_id'].unique()[:1000]:  # 限制前1000个玩家
            player_payments = payments_df[payments_df['player_id'] == player_id]
            player_sessions = sessions_df[sessions_df['player_id'] == player_id]
            
            if len(player_payments) > 1:  # 有多次付费的玩家
                total_spent = player_payments['actual_amount'].sum()
                avg_roi = player_sessions['roi_ratio'].mean()
                payment_frequency = len(player_payments)
                avg_satisfaction = player_payments['satisfaction_post_payment'].mean()
                
                                 # 分析付费模式
                 payment_intervals = []
                 sorted_payments = player_payments.sort_values(by='payment_time')
                 for i in range(1, len(sorted_payments)):
                     prev_time = datetime.strptime(str(sorted_payments.iloc[i-1]['payment_time']), "%Y-%m-%d %H:%M:%S")
                     curr_time = datetime.strptime(str(sorted_payments.iloc[i]['payment_time']), "%Y-%m-%d %H:%M:%S")
                     interval = (curr_time - prev_time).days
                     payment_intervals.append(interval)
                
                avg_interval = np.mean(payment_intervals) if payment_intervals else 0
                
                text = f"""
                付费行为分析：{player_id}
                
                付费概况：
                - 付费次数：{payment_frequency}次
                - 总付费金额：{total_spent:.2f}元
                - 平均单次付费：{total_spent/payment_frequency:.2f}元
                - 付费频率：平均每{avg_interval:.1f}天付费一次
                
                投资回报：
                - 平均投资回报率：{avg_roi:.2f}
                - 付费后满意度：{avg_satisfaction:.2f}/1.0
                - 总游戏场次：{len(player_sessions)}场
                - 付费场次占比：{len(player_payments)/len(player_sessions)*100:.1f}%
                
                付费模式分析：
                {'高频小额付费用户' if payment_frequency > 10 and total_spent/payment_frequency < 10 else '低频大额付费用户' if payment_frequency < 5 and total_spent/payment_frequency > 20 else '中等付费用户'}
                
                风险评估：
                {'投资回报较低，存在流失风险' if avg_roi < 0.8 else '投资回报良好，为高价值用户' if avg_roi > 1.5 else '投资回报中等，需持续关注'}
                
                运营建议：
                {'建议推荐低风险场次' if avg_roi < 1.0 else '建议推荐高级付费场次' if avg_roi > 2.0 else '建议推荐当前偏好的场次类型'}
                """
                
                documents.append({
                    "id": f"payment_analysis_{doc_id:06d}",
                    "text": text.strip(),
                    "metadata": json.dumps({
                        "document_type": "payment_analysis",
                        "player_id": player_id,
                        "total_spent": float(total_spent),
                        "payment_frequency": payment_frequency,
                        "avg_roi": float(avg_roi),
                        "avg_satisfaction": float(avg_satisfaction)
                    })
                })
                doc_id += 1
        
        return pd.DataFrame(documents)
    
    def _random_date(self, start_date: datetime, end_date: datetime) -> datetime:
        """生成随机日期"""
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        random_hours = random.randrange(24)
        random_minutes = random.randrange(60)
        
        return start_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
    
    def save_all_data(self, output_dir: str = "game_data"):
        """生成并保存所有数据"""
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/raw", exist_ok=True)
        os.makedirs(f"{output_dir}/input", exist_ok=True)
        
        print("正在生成玩家数据...")
        players_df = self.generate_players(10000)
        players_df.to_csv(f"{output_dir}/raw/players.csv", index=False, encoding='utf-8')
        
        print("正在生成场次数据...")
        rooms_df = self.generate_rooms(100)
        rooms_df.to_csv(f"{output_dir}/raw/rooms.csv", index=False, encoding='utf-8')
        
        print("正在生成游戏会话数据...")
        sessions_df = self.generate_game_sessions(players_df, rooms_df, 50000)
        sessions_df.to_csv(f"{output_dir}/raw/game_sessions.csv", index=False, encoding='utf-8')
        
        print("正在生成付费记录...")
        payments_df = self.generate_payment_records(sessions_df)
        payments_df.to_csv(f"{output_dir}/raw/payment_records.csv", index=False, encoding='utf-8')
        
        print("正在生成GraphRAG文档数据...")
        documents_df = self.generate_text_documents(players_df, rooms_df, sessions_df, payments_df)
        documents_df.to_csv(f"{output_dir}/input/documents.csv", index=False, encoding='utf-8')
        
        # 生成数据统计报告
        stats = {
            "数据生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "玩家总数": len(players_df),
            "场次总数": len(rooms_df),
            "游戏会话总数": len(sessions_df),
            "付费记录总数": len(payments_df),
            "文档总数": len(documents_df),
            "总收入": float(payments_df['actual_amount'].sum()),
            "平均玩家价值": float(payments_df.groupby('player_id')['actual_amount'].sum().mean()),
            "付费转化率": float(len(payments_df[payments_df['actual_amount'] > 0]) / len(sessions_df)),
            "平均满意度": float(sessions_df['satisfaction_rating'].mean())
        }
        
        with open(f"{output_dir}/data_stats.json", 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据生成完成！")
        print(f"输出目录: {output_dir}/")
        print(f"- 原始数据: {output_dir}/raw/")
        print(f"- GraphRAG输入: {output_dir}/input/")
        print(f"- 数据统计: {output_dir}/data_stats.json")
        print(f"\n数据统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        return players_df, rooms_df, sessions_df, payments_df, documents_df


if __name__ == "__main__":
    generator = GameDataGenerator()
    generator.save_all_data("game_data")
    
    print("\n使用说明:")
    print("1. 将 game_data/input/documents.csv 复制到你的GraphRAG项目的 input/ 目录")
    print("2. 运行 'graphrag index' 开始构建知识图谱")
    print("3. 使用 'graphrag query' 进行智能查询")
    print("\n示例查询:")
    print("- '哪些玩家有流失风险？'")
    print("- '高级付费场的收益情况如何？'")
    print("- '如何优化场次设置提升玩家满意度？'") 