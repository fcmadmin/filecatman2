#Namespace Container Class
class FCM:
    OnlyDisabled = 0
    OnlyEnabled = 1

    NoChildren = 2
    IsTags = 3
    NoTags = 4

    IsWeblinks = 2
    NoWeblinks = 3
    IsWebpages = 4
    NoWebpages = 5

    ItemCol = dict(
        Iden=0,Name=1,Type=2,Ext=3,Source=4,ModificationTime=5,CreationTime=6,Description=7,PrimaryCategory=8,Md5=9)
    CatCol = dict(
        Iden=0, Name=1, Taxonomy=2, Description=3, Parent=4, Count=5)