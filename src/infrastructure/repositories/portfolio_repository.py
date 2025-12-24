"""
Portfolio Repository - Infrastructure Layer
IPortfolioRepository 인터페이스의 JSON 파일 기반 구현체
"""
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.domain.repositories.interfaces import IPortfolioRepository
from src.domain.entities.stock import PortfolioEntity


class JSONPortfolioRepository(IPortfolioRepository):
    """
    JSON 파일 기반 포트폴리오 저장소
    
    사용 예:
        repo = JSONPortfolioRepository()
        repo.save(portfolio)
        loaded = repo.load("my_portfolio")
    """
    
    def __init__(self, storage_path: str = "data/portfolios"):
        """
        Args:
            storage_path: JSON 파일 저장 경로
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, portfolio: PortfolioEntity) -> bool:
        """포트폴리오 저장"""
        
        try:
            file_path = self.storage_path / f"{portfolio.portfolio_id}.json"
            
            # Entity → Dict
            data = {
                "portfolio_id": portfolio.portfolio_id,
                "name": portfolio.name,
                "holdings": portfolio.holdings,
                "cash": portfolio.cash,
                "created_at": portfolio.created_at.isoformat(),
                "updated_at": portfolio.updated_at.isoformat()
            }
            
            # JSON 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] JSONPortfolioRepository.save: {e}")
            return False
    
    def load(self, portfolio_id: str) -> Optional[PortfolioEntity]:
        """포트폴리오 조회"""
        
        try:
            file_path = self.storage_path / f"{portfolio_id}.json"
            
            if not file_path.exists():
                return None
            
            # JSON 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Dict → Entity
            portfolio = PortfolioEntity(
                portfolio_id=data["portfolio_id"],
                name=data["name"],
                holdings=data.get("holdings", {}),
                cash=data.get("cash", 0.0),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"])
            )
            
            return portfolio
            
        except Exception as e:
            print(f"[ERROR] JSONPortfolioRepository.load: {e}")
            return None
    
    def list_all(self) -> List[PortfolioEntity]:
        """모든 포트폴리오 목록 조회"""
        
        portfolios = []
        
        try:
            # .json 파일 검색
            for file_path in self.storage_path.glob("*.json"):
                portfolio_id = file_path.stem
                portfolio = self.load(portfolio_id)
                if portfolio:
                    portfolios.append(portfolio)
            
            return portfolios
            
        except Exception as e:
            print(f"[ERROR] JSONPortfolioRepository.list_all: {e}")
            return []
    
    def delete(self, portfolio_id: str) -> bool:
        """포트폴리오 삭제"""
        
        try:
            file_path = self.storage_path / f"{portfolio_id}.json"
            
            if file_path.exists():
                file_path.unlink()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"[ERROR] JSONPortfolioRepository.delete: {e}")
            return False


class SessionPortfolioRepository(IPortfolioRepository):
    """
    Streamlit Session State 기반 포트폴리오 저장소
    (런타임에만 유지, 재시작 시 초기화)
    """
    
    def __init__(self, session_state=None):
        """
        Args:
            session_state: Streamlit session_state 객체
        """
        self.session_state = session_state or {}
        
        if "portfolios" not in self.session_state:
            self.session_state["portfolios"] = {}
    
    def save(self, portfolio: PortfolioEntity) -> bool:
        """Session State에 저장"""
        try:
            self.session_state["portfolios"][portfolio.portfolio_id] = portfolio
            return True
        except Exception as e:
            print(f"[ERROR] SessionPortfolioRepository.save: {e}")
            return False
    
    def load(self, portfolio_id: str) -> Optional[PortfolioEntity]:
        """Session State에서 조회"""
        return self.session_state.get("portfolios", {}).get(portfolio_id)
    
    def list_all(self) -> List[PortfolioEntity]:
        """Session State의 모든 포트폴리오"""
        return list(self.session_state.get("portfolios", {}).values())
    
    def delete(self, portfolio_id: str) -> bool:
        """Session State에서 삭제"""
        try:
            portfolios = self.session_state.get("portfolios", {})
            if portfolio_id in portfolios:
                del portfolios[portfolio_id]
                return True
            return False
        except Exception as e:
            print(f"[ERROR] SessionPortfolioRepository.delete: {e}")
            return False
