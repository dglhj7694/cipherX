# ══════════════════════════════════════════════════════════════
#  sectors.py — 섹터별 티커 그룹 관리 (2026 Q2 리팩터)
#  대분류 9개 → 세부 섹터 27개 2단계 구조
#  하나의 티커가 여러 섹터에 중복 포함 가능
# ══════════════════════════════════════════════════════════════

SECTOR_GROUPS = {

    # ══════════════════════════════════════════════════════════
    # [대분류 1] 전략 포트폴리오
    # ══════════════════════════════════════════════════════════

    'TOP 워치리스트': [
        'PLAB', 'INOD', 'MYRG', 'LEU',  'MOD',  'SKYT', 'AEHR', 'ASYS',
        'RFIL', 'CRDO', 'FN',   'CAMT', 'NVMI', 'FIVN', 'SMR',  'NNE',
        'SERV', 'MP',   'KLIC', 'APLD', 'PENG',
    ],

    '2026 로드맵': [
        # 반도체
        'NVDA', 'AVGO', 'MRVL', 'AMD',  'ARM',  'MPWR', 'QCOM', 'TSM',  'ASML',
        'AMAT', 'LRCX', 'KLAC',
        # 전력/인프라
        'VRT',  'ETN',  'GEV',  'PWR',  'NVT',  'ANET',
        # 광통신
        'COHR', 'CIEN', 'FN',
        # 에너지
        'CEG',  'VST',  'CCJ',  'OKLO', 'SMR',  'NEE',
        # AI/로봇/자율
        'ISRG', 'SYM',  'SERV', 'PATH', 'PLTR', 'TSLA',
        # 클라우드/보안
        'SNOW', 'MDB',  'CRWD', 'PANW', 'DDOG', 'NET',  'ZS',   'S',
        # 바이오/우주/소재
        'RXRX', 'SDGR', 'RKLB', 'ASTS', 'MP',   'SNDK',
    ],

    '주도섹터 공격': [
        'AAOI', 'ALAB', 'AMKR', 'ARM',  'ASTS', 'AVAV', 'BAH',  'BE',   'BEAM', 'BWXT',
        'CAMT', 'CPRX', 'CRSP', 'CRX',  'DOCN', 'ELF',  'EXAS', 'FIX',  'FLNC', 'FN',
        'GNRC', 'GTLS', 'HALO', 'HUBS', 'ITRI', 'KPTI', 'KTOS', 'LMT',  'LRCX', 'LUNR',
        'MNMD', 'MOD',  'MRVL', 'MSTR', 'MU',   'MYRG', 'NVDA', 'NVT',  'ONDS', 'ORCL',
        'PL',   'PLTR', 'POWL', 'PTGX', 'RKLB', 'SATS', 'SIDU', 'SPCE', 'STRL', 'TER',
        'TTMI', 'UCTT', 'VRT',  'XENE',
    ],

    '주도섹터 방어': [
        'ABBV',  'ACN',  'ADP',  'APD',   'AROC',  'BRK.B', 'CEG',  'CLX',
        'COST',  'CPB',  'CVX',  'DHR',   'DUK',   'EQT',   'EXP',  'FTI',
        'JNJ',   'JPM',  'KO',   'LIN',   'MMC',   'MSFT',  'NEE',  'NUE',
        'PAYX',  'PEP',  'PG',   'RTX',   'SCCO',  'STZ',   'TMO',  'VST',
        'WM',    'WMT',  'XOM',  'ZBH',
    ],

    # ──────────────────────────────────────────────────────────
    # 전시 바벨 (2026-03-27)
    # ──────────────────────────────────────────────────────────
    '전시바벨 공격 [2026-03]': [
        # 방산/무인
        'AVAV', 'KTOS', 'RCAT', 'BWXT', 'LDOS',
        # 전력/인프라
        'VRT',  'FTI',
        # 광통신
        'LITE', 'COHR', 'RDWR', 'INSG',
        # 에너지 탱커/유전
        'FRO',  'STNG', 'DHT',  'NAT',  'TALO',
        # 유전서비스
        'PUMP', 'WFRD', 'NOG',  'ARCH',
    ],

    '전시바벨 방어 [2026-03]': [
        'XOM',  'CVX',  'LMT',  'RTX',  'NOC',
        'GD',   'HII',  'PANW', 'CSCO', 'UNH',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 2] 반도체 / 하드웨어
    # ══════════════════════════════════════════════════════════

    '칩설계/가속기': [
        'NVDA', 'AVGO', 'MRVL', 'AMD',  'ARM',  'MPWR',
        'QCOM', 'INTC', 'LSCC', 'ON',   'MU',   'MCHP',
    ],

    '반도체장비/소재': [
        # 전공정 장비 (WFE)
        'ASML', 'AMAT', 'LRCX', 'KLAC', 'TER',  'UCTT', 'ACMR',
        # 후공정/패키징
        'KLIC', 'AMKR', 'COHU',
        # 특수장비/검사
        'AEHR', 'ASYS', 'CAMT', 'NVMI', 'FORM', 'ONTO', 'ACLS',
        # 소재/부품
        'PLAB', 'SKYT', 'ENTG', 'WOLF', 'VECO', 'GFS',  'ATOM',
    ],

    '네트워킹/광통신': [
        # 광트랜시버/광소자
        'CRDO', 'FN',   'COHR', 'LITE', 'CIEN', 'ALAB', 'AAOI',
        'LASR', 'POET', 'LWLG', 'VIAV', 'INFN',
        # RF/아날로그
        'MTSI', 'MKSI', 'TSEM',
        # 스위치/라우터
        'ANET', 'CSCO',
        # 케이블/커넥터
        'APH',  'GLW',  'DY',
        # CDN/네트워크
        'AKAM', 'HLIT', 'INSG', 'CLS',  'ASX',
    ],

    '스토리지/메모리': [
        'MU',   'WDC',  'STX',  'PSTG',
        'PENG', 'NTAP', 'DELL', 'SNDK',
    ],

    '냉각/열관리': [
        'MOD',  'FIX',  'NVT',  'VRT',
        'SMCI', 'RFIL', 'AA',   'CARR', 'JCI',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 3] AI / 소프트웨어
    # ══════════════════════════════════════════════════════════

    'AI플랫폼/SW': [
        # AI 인프라/모델
        'PLTR', 'SNOW', 'MDB',  'CRWV', 'NBIS', 'ORCL',
        # AI 애플리케이션
        'INOD', 'FIVN', 'SOUN', 'APP',  'TEM',  'ZETA', 'U',    'PGY',
        # 데이터/분석
        'DDOG', 'TDC',  'RSKD', 'PUBM', 'MANH', 'TYL',  'GWRE', 'CVLT',
        # 기업 SW
        'NOW',  'CRM',  'ADBE', 'MSFT', 'HUBS', 'META', 'TEAM', 'DUOL',
        'CHKP', 'FTNT', 'PANW',
        # 특화 AI
        'BOX',  'FROG', 'KVYO', 'AI',   'UPST',
    ],

    '클라우드/데이터': [
        'SNOW', 'MDB',  'NET',  'TEAM', 'DDOG', 'PLTR', 'VRNS',
        'FSLY', 'APPN', 'ZETA', 'DOCN', 'TENB',
    ],

    '사이버보안': [
        'CRWD', 'PANW', 'ZS',   'NET',  'S',    'FTNT',
        'OKTA', 'RBRK', 'CYBR', 'VRNS', 'QLYS', 'TENB',
        'BB',   'CACI',
    ],

    '로보틱스/물리AI': [
        # 로봇 플랫폼
        'SYM',   'SERV',  'ISRG',  'ROK',   'ABB',   'FANUY', 'SYK',
        # 자율주행/센서
        'TSLA',  'MBLY',  'AUR',   'HSAI',  'LAZR',  'LIDR',  'INVZ',  'EVLV',
        # UAV/드론
        'AVAV',  'ACHR',  'JOBY',  'RR',
        # 산업자동화/모션
        'TER',   'KTOS',  'AXON',  'PATH',
        'RRX',   'PH',    'EMR',   'TKR',   'ST',    'MEI',
        # AI 음성/엣지
        'SOUN',  'AI',    'BBAI',  'INOD',  'AMBA',
        # 비전/정밀측정
        'CGNX',  'KEYS',  'ZBRA',  'ALNT',  'ADI',   'TRMB',
        # 연결/전력/기타부품
        'TEL',   'APH',   'VICR',  'ON',    'CW',    'TDY',
        'PTC',   'STRC',  'NOVT',
    ],

    '양자컴퓨팅/차세대기술': [
        # 퀀텀 하드웨어
        'IONQ', 'RGTI', 'QBTS', 'QUBT', 'ARQQ',
        # 퀀텀 소프트웨어/연계
        'SKYT', 'RKTA',
        # 차세대 기술 (광·전력반도체·기타)
        'ACMR', 'AMBA', 'VICR', 'HLIT',
        'SEVA', 'MG',   'POWW',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 4] 에너지 / 전력인프라
    # ══════════════════════════════════════════════════════════

    '전력/산업인프라': [
        # 전력 장비·시스템
        'VRT',  'ETN',  'GEV',  'PWR',  'NVT',  'HUBB', 'ITRI',
        'POWL', 'FIX',  'STRL', 'GNRC', 'WMS',  'PNR',  'VLTO',
        # 산업 자동화·계측
        'EMR',  'HON',  'MOD',  'TDY',  'KEYS', 'CGNX', 'TRMB', 'PTC',
        'MRCY', 'TKR',  'CW',   'AY',   'PSN',
        # 전력망 건설·유틸리티
        'MYRG', 'EME',  'MTZ',  'IESC', 'PLPC', 'DUK',  'NEE',
        'TLN',  'SEI',
        # AI 데이터센터 전력
        'AEIS', 'AMSC', 'APLD',
    ],

    '원자력/SMR': [
        # SMR 개발·운영
        'SMR',  'OKLO', 'NNE',  'BWXT', 'LTBR',
        # 핵연료·우라늄
        'LEU',  'CCJ',  'UEC',  'NXE',  'UUUU',
        'DNN',  'UROY', 'URG',  'EU',   'ISO',
        # 원전 EPC·설계
        'FLR',
        # 원전 수혜 유틸리티
        'CEG',  'VST',
    ],

    '차세대에너지': [
        # 재생에너지
        'ENPH', 'SEDG', 'RUN',  'FLNC', 'STEM', 'NPWR',
        # 배터리 저장
        'BE',   'ENS',  'GWH',  'EOS',  'SLRC',
        # 수소·기타
        'NRGV',
        # AI 데이터센터 에너지
        'APLD',
        # 원자력 (차세대)
        'OKLO', 'SMR',  'NNE',  'LEU',  'BWXT', 'LTBR',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 5] 빅테크 / 플랫폼
    # ══════════════════════════════════════════════════════════

    '빅테크/플랫폼': [
        'MSFT', 'AMZN', 'GOOGL', 'META', 'AAPL', 'IBM',
        'DELL', 'HPE',  'RBLX',  'RDDT', 'RUM',
    ],

    'NVDA 생태계/AI인프라파트너': [
        # AI 인프라·에너지
        'SMR',  'CEG',  'VRT',  'EQIX',
        # 반도체·광통신
        'INTC', 'TSM',  'COHR', 'LITE', 'ARM',  'ASML',
        # 하이퍼스케일러
        'MSFT', 'GOOGL','AMZN', 'META',
        # AI 응용·차세대
        'IONQ', 'TSLA', 'PATH', 'RXRX', 'SDGR', 'PLTR',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 6] 방산 / 우주 / 보안
    # ══════════════════════════════════════════════════════════

    '방산/보안': [
        # 전통 방산
        'LMT',  'RTX',  'NOC',  'LHX',  'GD',   'HII',
        # 사이버·C4ISR
        'HON',  'CACI', 'PSN',  'KTOS',
        # 사이버보안 (방산 연계)
        'CRWD', 'PANW', 'FTNT', 'OKTA',
    ],

    '우주/항공/UAM': [
        # 발사체·위성 제조
        'RKLB', 'ASTS', 'LUNR', 'RDW',  'MNTS',
        # 위성 데이터·통신
        'PL',   'SPIR', 'BKSY', 'GSAT', 'IRDM', 'SATS', 'VSAT',
        # UAM/eVTOL
        'ACHR', 'JOBY',
        # 무인기·드론
        'AVAV', 'KTOS',
        # 저궤도 기타
        'SIDU', 'LLAP',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 7] 바이오 / 헬스
    # ══════════════════════════════════════════════════════════

    '바이오/헬스': [
        # AI 신약·유전체
        'RXRX', 'SDGR', 'DNLI', 'ABCL', 'TEM',
        # 유전자편집·시퀀싱
        'EDIT', 'BEAM', 'NTLA', 'PACB', 'TWST', 'TXG',  'WGS',  'DNA',
        # 진단·액체생검
        'EXAS', 'VCYT', 'NTRA', 'GH',   'GRAL',
        # 디지털헬스
        'HIMS', 'GDRX', 'AMWL', 'SOPH',
        # 특수 치료제
        'TGTX', 'VKTX', 'HLNX', 'TMDX', 'PRME', 'UTHR',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 8] 원자재 / 자원
    # ══════════════════════════════════════════════════════════

    '우라늄/핵연료': [
        'CCJ',  'UEC',  'NXE',  'UUUU', 'DNN',
        'UROY', 'URG',  'EU',   'LEU',  'BWXT', 'ISO',
    ],

    '리튬/배터리': [
        # 리튬 채굴·정제
        'ALB',  'SQM',  'LAC',  'SGML', 'IONR', 'NMG',  'PLL',
        # 배터리 셀·소재
        'NVX',  'ATLX', 'ELBM', 'DFLI', 'LICY', 'FREY',
        # 전고체
        'QS',   'SLDP',
        # 반도체 관련 소재
        'WOLF',
    ],

    '구리/베이스메탈': [
        'FCX',  'SCCO', 'RIO',  'HBM',  'ERO',
        'TGB',  'IE',   'TMQ',  'KOS',
    ],

    '희토류/특수소재': [
        # 희토류 채굴·분리
        'MP',   'UAMY', 'NB',   'IPX',  'PPTA', 'IDR',  'CRML',
        # 특수소재·복합재
        'TROX', 'MTRN', 'COHR', 'PLPC', 'HXL',
    ],


    # ══════════════════════════════════════════════════════════
    # [대분류 9] 핀테크 / 크립토
    # ══════════════════════════════════════════════════════════

    '핀테크/디지털금융': [
        # 결제·대출
        'COIN', 'SQ',   'SOFI', 'HOOD', 'AFRM', 'UPST', 'MQ',
        # 인슈어테크
        'LMND',
        # 글로벌 이커머스·핀테크
        'GLBE', 'JMIA', 'DLO',  'WRBY',
        # 소셜·크리에이터 플랫폼
        'RBLX', 'RDDT', 'RUM',
    ],

    '비트코인채굴/디지털자산': [
        'MARA', 'IREN', 'CLSK', 'WULF', 'BTMW',
    ],

    '모건스탠리 Space 60': [
        # 원자재 / 소재 / 가스
        'MP', 'FCX', 'AA', 'TECK', 'CRS', 'ATI', 'MTRN', 'GLW', 'HXL', 'PKE',
        'LIN', 'APD', 'NEU',

        # 반도체 / RF / 광학 / 네트워크
        'ADI', 'STM', 'MCHP', 'QRVO', 'MRCY', 'TTMI', 'AVGO', 'COHR', 'LITE', 'NVDA', 'TDY',

        # 부품 / 센서 / 연결 / 추진 하위부품
        'RBC', 'PH', 'AME', 'APH', 'APTV', 'MOG.A', 'GHM', 'KRMN', 'HON',

        # 우주 / 항공 / 발사 / 플랫폼
        'RDW', 'RKLB', 'BA', 'NOC', 'LMT', 'KTOS', 'VOYG', 'LUNR', 'RTX',

        # 위성통신 / 지상시스템 / 지구관측
        'GILT', 'VSAT', 'ASTS', 'IRDM', 'AMZN', 'GSAT', 'PL', 'BKSY', 'SPIR', 'TSAT',
    ],
}