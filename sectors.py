# ══════════════════════════════════════════════════════════════
#  sectors.py — 섹터별 티커 그룹 관리
#  새 섹터 추가: SECTOR_GROUPS에 딕셔너리 항목만 추가하면 됩니다
# ══════════════════════════════════════════════════════════════

SECTOR_GROUPS = {
    'TOP': [
        'PLAB', 'INOD', 'MYRG', 'LEU', 'MOD', 'SKYT', 'AEHR', 'ASYS', 'RFIL', 'CRDO',
        'FN', 'CAMT', 'NVMI', 'FIVN', 'SMR', 'NNE', 'SERV', 'MP', 'KLIC', 'APLD', 'PENG'
    ],

    # 🚀 2026 로드맵 전체 스캔
    '2026': [
        'NVDA', 'AVGO', 'MRVL', 'AMD', 'ARM', 'MPWR', 'QCOM', 'TSM', 'ASML', 
        'AMAT', 'LRCX', 'KLAC', 'VRT', 'ETN', 'GEV', 'PWR', 'NVT', 'ANET', 
        'COHR', 'CIEN', 'FN', 'CEG', 'VST', 'CCJ', 'OKLO', 'SMR', 'NEE', 
        'ISRG', 'SYM', 'SERV', 'PATH', 'PLTR', 'SNOW', 'MDB', 'TSLA', 
        'CRWD', 'PANW', 'DDOG', 'NET', 'ZS', 'S', 'RXRX', 'SDGR', 'RKLB', 
        'ASTS', 'MP'
    ],

    # 🔍 X10 세부 섹터
    'X10 냉각/열관리': ['MOD', 'FIX', 'NVT', 'SMCI', 'RFIL', 'AA', 'CARR', 'JCI', 'VRT'],
    'X10 전력/인프라': ['MYRG', 'EME', 'PWR', 'PLPC', 'IESC', 'MTZ', 'DUK', 'TLN', 'SEI', 'APLD', 'IREN', 'WULF', 'HUT', 'AEIS', 'AMSC', 'BE', 'ETN', 'GEV', 'NEE'],
    'X10 반도체장비/소재': ['PLAB', 'AEHR', 'SKYT', 'ASYS', 'CAMT', 'NVMI', 'KLIC', 'AMKR', 'ENTG', 'FORM', 'ACMR', 'ATOM', 'GFS', 'WOLF', 'ASML', 'LRCX', 'KLAC'],
    'X10 칩설계/가속기': ['NVDA', 'AVGO', 'MRVL', 'AMD', 'ARM', 'MPWR', 'QCOM', 'INTC'],
    'X10 네트워킹/광통신': ['CRDO', 'FN', 'COHR', 'LITE', 'CIEN', 'MTSI', 'MKSI', 'ALAB', 'CLS', 'AKAM', 'HLIT', 'INSG', 'ANET'],
    'X10 원자력/SMR': ['SMR', 'OKLO', 'LEU', 'BWXT', 'CCJ', 'VST', 'CEG', 'FLR', 'UEC', 'NNE'],
    'X10 로보틱스/물리AI': ['SYM', 'SERV', 'TER', 'KTOS', 'ISRG', 'ROK', 'AXON', 'PATH', 'TSLA', 'EVLV', 'LIDR', 'HSAI'],
    'X10 사이버보안': ['S', 'QLYS', 'CYBR', 'VRNS', 'FTNT', 'RBRK', 'BB', 'PANW', 'CRWD', 'ZS', 'NET'],
    'X10 스토리지/메모리': ['SNDK', 'WDC', 'MU', 'STX', 'PSTG', 'PENG', 'NTAP', 'DELL'],
    'X10 AI플랫폼/SW': ['INOD', 'FIVN', 'TDC', 'BOX', 'CRWV', 'NBIS', 'PLTR', 'SNOW', 'MDB', 'SOUN', 'RSKD', 'PUBM'],
    'X10 우주/바이오/자원': ['RKLB', 'ASTS', 'RDW', 'IRDM', 'GSAT', 'VSAT', 'RXRX', 'SDGR', 'MP', 'SLI'],

    # 🧬 특수 테마
    '양자컴퓨팅': ['IONQ', 'RGTI', 'QBTS', 'QUBT', 'ARQQ', 'SKYT'],
    # 🖥️ 기존 이미지(IMG) 기반 리스트
    '소프트웨어': ['FTNT', 'MANH', 'CHKP', 'TEAM', 'DUOL', 'CVLT', 'DDOG', 'TYL', 'PANW', 'NOW', 'MSFT', 'HUBS', 'META', 'SNOW', 'CRWD', 'ZS', 'GWRE', 'RBRK', 'S', 'ORCL', 'UPST', 'INOD', 'ZETA', 'U', 'TEM', 'PGY', 'APP', 'FROG', 'KVYO', 'OKTA', 'NET', 'PLTR', 'MDB', 'AI', 'CRM', 'ADBE'],
    '로봇/자동화': ['RRX', 'TDY', 'AMBA', 'ISRG', 'AMAT', 'KEYS', 'TEL', 'TKR', 'ST', 'PTC', 'MEI', 'PH', 'ZBRA', 'ALNT', 'QCOM', 'ADI', 'CW', 'CGNX', 'ON', 'TSLA', 'ROK', 'RKT', 'APH', 'PATH', 'VICR', 'RR', 'SERV', 'SYM', 'STRC', 'TER', 'NOVT', 'ABB', 'FANUY', 'SYK', 'MBLY', 'EMR'],
    '광통신': ['CSCO', 'AVGO', 'CW', 'NVDA', 'MRVL', 'INTC', 'FN', 'TSM', 'ASX', 'GLW', 'LASR', 'LITE', 'ALAB', 'CRDO', 'COHR', 'POET', 'AAOI', 'TSEM', 'LWLG', 'CIEN', 'ANET', 'INFN', 'VIAV', 'DY', 'APH']
}